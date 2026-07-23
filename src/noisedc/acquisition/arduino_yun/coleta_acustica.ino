/*
 * NoiseDC — Camada 1: aquisição acústica
 * Plataforma: Arduino Yún (ATmega32U4 + AR9331 com Linux embarcado)
 * Sensor:     KY-037 (microfone de eletreto + comparador LM393), saída analógica
 *
 * A leitura usa a saída analógica (AO) do módulo, digitalizada pelo ADC de
 * 10 bits do ATmega32U4 à taxa de 22.050 Hz. A saída digital (DO) do KY-037 é
 * ignorada: ela apenas comuta quando um limiar ajustável é ultrapassado, o que
 * descarta a forma de onda de que a análise espectral depende.
 *
 * A profundidade de 16 bits abaixo refere-se ao formato de armazenamento .wav;
 * a resolução efetiva permanece limitada aos 10 bits do conversor. Por isso o
 * protótipo é instrumento de análise relativa de padrões acústicos, e não de
 * medição absoluta de nível sonoro.
 *
 * ---------------------------------------------------------------------------
 * ATENÇÃO — credenciais
 * ---------------------------------------------------------------------------
 * Os marcadores abaixo devem ser preenchidos localmente e NUNCA versionados
 * com valores reais. Antes de qualquer commit, confirme que este arquivo
 * continua com os marcadores intactos:
 *
 *     grep -n "PREENCHER" coleta_acustica.ino
 *
 * A credencial de Wi-Fi embutida em firmware é a via mais comum de vazamento
 * de acesso à rede em projetos acadêmicos de IoT.
 * ---------------------------------------------------------------------------
 */

#include <Bridge.h>
#include <Process.h>

// ---------------------------------------------------------------------------
// Configuração — preencher localmente
// ---------------------------------------------------------------------------
const char* WIFI_SSID  = "<PREENCHER_SSID>";
const char* WIFI_SENHA = "<PREENCHER_SENHA>";
const char* DIRETORIO_GRAVACOES = "/mnt/sda1/gravacoes";

// ---------------------------------------------------------------------------
// Parâmetros de aquisição
// ---------------------------------------------------------------------------
const int  PINO_SENSOR        = A0;      // saída analógica do KY-037
const long TAXA_AMOSTRAGEM_HZ = 22050;   // cobertura espectral até ~11 kHz
const int  DURACAO_SEGUNDOS   = 60;      // duração de cada gravação
const int  INTERVALO_MINUTOS  = 15;      // espera entre gravações

const unsigned long INTERVALO_AMOSTRA_US = 1000000UL / TAXA_AMOSTRAGEM_HZ;
const int TAMANHO_BUFFER = 256;

int16_t buffer[TAMANHO_BUFFER];
int posicaoBuffer = 0;

void setup() {
  Bridge.begin();
  Serial.begin(115200);
  analogReference(DEFAULT);   // referência de 5 V, compatível com a saída do sensor

  // O ADC do ATmega32U4 opera com prescaler; o valor abaixo reduz o tempo de
  // conversão o suficiente para sustentar 22.050 Hz de forma estável.
  ADCSRA = (ADCSRA & 0xF8) | 0x04;

  aguardarSistemaDeArquivos();
  Serial.println(F("NoiseDC — Camada 1 pronta."));
}

void loop() {
  String nomeArquivo = montarNomeArquivo();
  gravar(nomeArquivo, DURACAO_SEGUNDOS);
  Serial.print(F("Gravação concluída: "));
  Serial.println(nomeArquivo);

  delay((unsigned long)INTERVALO_MINUTOS * 60UL * 1000UL);
}

/*
 * Aguarda a montagem do armazenamento no lado Linux. Sem essa espera, as
 * primeiras gravações após o boot são perdidas silenciosamente.
 */
void aguardarSistemaDeArquivos() {
  Process p;
  for (int tentativa = 0; tentativa < 30; tentativa++) {
    p.runShellCommand(String("test -d ") + DIRETORIO_GRAVACOES + " && echo ok");
    String resposta = "";
    while (p.available()) {
      resposta += (char)p.read();
    }
    if (resposta.indexOf("ok") >= 0) {
      return;
    }
    delay(1000);
  }
  Serial.println(F("AVISO: diretório de gravações indisponível."));
}

/*
 * Nome no formato AAAA-MM-DD_HHMM_<estado>.wav.
 *
 * O estado é anexado depois, no servidor, pelo módulo de transferência: a
 * rotulagem de anomalia depende de evidência externa e não pode ser decidida
 * pelo dispositivo.
 */
String montarNomeArquivo() {
  Process data;
  data.runShellCommand("date +%Y-%m-%d_%H%M");

  String marca = "";
  while (data.available()) {
    char c = data.read();
    if (c != '\n' && c != '\r') {
      marca += c;
    }
  }
  return String(DIRETORIO_GRAVACOES) + "/" + marca + "_coleta.wav";
}

/*
 * Amostragem por temporização explícita. A leitura é escrita em blocos para
 * o lado Linux, que monta o contêiner .wav — o ATmega32U4 não tem memória
 * para acumular 60 s de áudio.
 */
void gravar(const String& caminho, int segundos) {
  Process escrita;
  escrita.begin("/usr/bin/env");
  escrita.addParameter("sh");
  escrita.addParameter("-c");
  escrita.addParameter(
    String("cat > ") + caminho + ".raw"
  );
  escrita.runAsynchronously();

  const unsigned long totalAmostras = (unsigned long)segundos * TAXA_AMOSTRAGEM_HZ;
  unsigned long proximaAmostra = micros();

  for (unsigned long i = 0; i < totalAmostras; i++) {
    while ((long)(micros() - proximaAmostra) < 0) {
      // espera ativa: em 22.050 Hz o intervalo é de ~45 us, curto demais
      // para um delay() confiável
    }
    proximaAmostra += INTERVALO_AMOSTRA_US;

    // Centraliza a leitura de 10 bits (0..1023) em torno de zero e escala
    // para a faixa de 16 bits do contêiner de saída.
    int leitura = analogRead(PINO_SENSOR);
    buffer[posicaoBuffer++] = (int16_t)((leitura - 512) << 5);

    if (posicaoBuffer >= TAMANHO_BUFFER) {
      escrita.write((uint8_t*)buffer, sizeof(buffer));
      posicaoBuffer = 0;
    }
  }

  if (posicaoBuffer > 0) {
    escrita.write((uint8_t*)buffer, posicaoBuffer * sizeof(int16_t));
    posicaoBuffer = 0;
  }
  escrita.close();

  converterParaWav(caminho);
}

/*
 * Converte o fluxo bruto em contêiner .wav no lado Linux, onde há sox ou
 * ffmpeg disponíveis. Manter a conversão fora do microcontrolador preserva a
 * temporização da aquisição.
 */
void converterParaWav(const String& caminho) {
  Process conversao;
  conversao.runShellCommand(
    String("sox -t raw -r ") + TAXA_AMOSTRAGEM_HZ +
    " -e signed -b 16 -c 1 " + caminho + ".raw " + caminho +
    " && rm -f " + caminho + ".raw"
  );
  while (conversao.running()) {
    delay(100);
  }
}
