#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Camada 3 — script autoritativo de reprodução (Linha C, EV09–EV14).

Reproduz as tabelas e figuras do Capítulo 5:
  - Tabela "por unidade" (leave-one-unit-out, nível de segmento)
  - Tabela "intra-distribuição" (leave-one-recording-out)
  - Tabela "decisão por gravação" (agregação por voto majoritário, LOUO)
  - Matriz de confusão do One-Class SVM (por unidade)
  - Figuras: ROC (LOUO), comparação de regimes, importância MFCC,
    escores One-Class, desempenho por unidade.

Entrada: features_segmentos.csv produzido pela Camada 2
  (colunas: sample_id, evaporadora, linha, classe, condicao, seg_idx,
   mfcc{1..20}_mean, mfcc{1..20}_std, dmfcc{1..20}_mean, rms, zcr, centroid, rolloff).

Coorte de análise binária: condicao in {OK, ANOMALIA}.
Descritor por segmento: 60 dimensões (média e desvio dos 20 MFCC + média dos 20 deltas).
"""
import csv, json, warnings
from pathlib import Path
from collections import defaultdict
import numpy as np
warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, OneClassSVM
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, roc_curve, confusion_matrix)

# --- caminhos (ajuste conforme sua árvore) ---
FEATURES = Path("dataset_linhaC/04_resultados/features_segmentos.csv")
FIG      = Path("figuras"); FIG.mkdir(parents=True, exist_ok=True)
SEED     = 42

rows = list(csv.DictReader(open(FEATURES)))
coh  = [r for r in rows if r["condicao"] in ("OK", "ANOMALIA")]
mcols = [k for k in rows[0] if k.startswith(("mfcc", "dmfcc"))]
X   = np.array([[float(r[c]) for c in mcols] for r in coh])
y   = np.array([1 if r["condicao"] == "ANOMALIA" else 0 for r in coh])
g   = np.array([int(r["evaporadora"]) for r in coh])
ids = np.array([r["sample_id"] for r in coh])
print(f"Segmentos: {len(y)} | normal={int((y==0).sum())} anomalia={int((y==1).sum())} | unidades={sorted(set(g))}")
logo = LeaveOneGroupOut()

def fpr(cm): tn, fp = cm[0][0], cm[0][1]; return fp/(fp+tn) if (fp+tn) else 0.0
def seg_row(name, yt, yp, sc):
    cm = confusion_matrix(yt, yp, labels=[0,1]).tolist()
    print(f"  {name:26s} acc={accuracy_score(yt,yp):.3f} prec={precision_score(yt,yp,zero_division=0):.3f} "
          f"rec={recall_score(yt,yp,zero_division=0):.3f} f1={f1_score(yt,yp,zero_division=0):.3f} "
          f"auc={roc_auc_score(yt,sc):.3f} fpr={fpr(cm):.3f}  cm={cm}")
def aggregate(ids, yp, sc, yt):
    by, scd, tru = defaultdict(list), defaultdict(list), {}
    for i,p,s,t in zip(ids,yp,sc,yt): by[i].append(p); scd[i].append(s); tru[i]=t
    rid=sorted(by)
    rp=np.array([1 if np.mean(by[i])>=0.5 else 0 for i in rid])  # voto majoritário
    rs=np.array([np.mean(scd[i]) for i in rid]); rt=np.array([tru[i] for i in rid])
    return rp, rs, rt

scores = {}

print("\n[1] Por unidade (leave-one-unit-out, segmento):")
# Baseline: melhor característica por fold + limiar de Youden
yp_b=np.zeros_like(y); sc_b=np.zeros(len(y))
for tr,te in logo.split(X,y,g):
    aucs=[roc_auc_score(y[tr],X[tr,k]) if len(set(y[tr]))>1 else .5 for k in range(X.shape[1])]
    k=int(np.argmax(np.abs(np.array(aucs)-.5))); s=1 if aucs[k]>=.5 else -1
    fprc,tprc,thr=roc_curve(y[tr],s*X[tr,k]); j=np.argmax(tprc-fprc); t=thr[j]
    sc_b[te]=s*X[te,k]; yp_b[te]=(s*X[te,k]>=t).astype(int)
seg_row("Baseline (1 caracteristica)",y,yp_b,sc_b); scores["baseline"]=sc_b

svm=make_pipeline(StandardScaler(),SVC(kernel="rbf",C=10,probability=True,class_weight="balanced"))
yp_s=cross_val_predict(svm,X,y,groups=g,cv=logo)
sc_s=cross_val_predict(svm,X,y,groups=g,cv=logo,method="predict_proba")[:,1]
seg_row("SVM (RBF)",y,yp_s,sc_s); scores["svm"]=sc_s

rf=RandomForestClassifier(n_estimators=400,class_weight="balanced",random_state=SEED)
yp_r=cross_val_predict(rf,X,y,groups=g,cv=logo)
sc_r=cross_val_predict(rf,X,y,groups=g,cv=logo,method="predict_proba")[:,1]
seg_row("Floresta Aleatoria",y,yp_r,sc_r); scores["random_forest"]=sc_r
rf.fit(StandardScaler().fit_transform(X),y); imp=rf.feature_importances_

yp_o=np.zeros_like(y); sc_o=np.zeros(len(y))
for tr,te in logo.split(X,y,g):
    Xn=X[tr][y[tr]==0]; sca=StandardScaler().fit(Xn)
    oc=OneClassSVM(kernel="rbf",gamma="scale",nu=0.1).fit(sca.transform(Xn))
    sc_o[te]=-oc.decision_function(sca.transform(X[te])); yp_o[te]=(oc.predict(sca.transform(X[te]))==-1).astype(int)
seg_row("One-Class SVM",y,yp_o,sc_o); scores["one_class_svm"]=sc_o
print("  Matriz OCSVM (por unidade):", confusion_matrix(y,yp_o,labels=[0,1]).tolist())

print("\n[2] Decisao por gravacao (voto majoritario, LOUO):")
for name,yp,sc in [("Baseline",yp_b,sc_b),("SVM",yp_s,sc_s),("Floresta Aleatoria",yp_r,sc_r),("One-Class SVM",yp_o,sc_o)]:
    rp,rs,rt=aggregate(ids,yp,sc,y)
    cm=confusion_matrix(rt,rp,labels=[0,1]).tolist()
    print(f"  {name:26s} acc={accuracy_score(rt,rp):.3f} prec={precision_score(rt,rp,zero_division=0):.3f} "
          f"rec={recall_score(rt,rp,zero_division=0):.3f} f1={f1_score(rt,rp,zero_division=0):.3f} "
          f"auc={roc_auc_score(rt,rs):.3f}  cm={cm}")

print("\n[3] Intra-distribuicao (leave-one-recording-out):")
for name,clf in [("SVM",make_pipeline(StandardScaler(),SVC(kernel="rbf",C=10,probability=True,class_weight="balanced"))),
                 ("Floresta Aleatoria",RandomForestClassifier(n_estimators=400,class_weight="balanced",random_state=SEED))]:
    sc=cross_val_predict(clf,X,y,groups=ids,cv=logo,method="predict_proba")[:,1]
    rp,rs,rt=aggregate(ids,(sc>=.5).astype(int),sc,y)
    print(f"  {name:26s} seg_AUC={roc_auc_score(y,sc):.3f}  rec_AUC={roc_auc_score(rt,rs):.3f}")

# ===== FIGURAS =====
plt.figure(figsize=(5,4.5))
for m,lab in [("svm","SVM"),("random_forest","Floresta Aleatória"),("one_class_svm","One-Class SVM"),("baseline","Baseline")]:
    fprc,tprc,_=roc_curve(y,scores[m]); plt.plot(fprc,tprc,label=f"{lab} (AUC={roc_auc_score(y,scores[m]):.2f})")
plt.plot([0,1],[0,1],"k--",lw=.8);plt.xlabel("Taxa de falsos positivos");plt.ylabel("Taxa de verdadeiros positivos")
plt.title("Curvas ROC — Camada 3 (leave-one-unit-out, segmento)");plt.legend(loc="lower right")
plt.tight_layout();plt.savefig(FIG/"roc_camada3.png",dpi=150);plt.close()

ordem=np.argsort(imp)[::-1][:15]
plt.figure(figsize=(7,4));plt.bar(range(len(ordem)),imp[ordem],color="#2E6CA4")
plt.xticks(range(len(ordem)),[mcols[k] for k in ordem],rotation=60,ha="right",fontsize=8)
plt.ylabel("Importância");plt.title("Importância das características MFCC (Floresta Aleatória)")
plt.tight_layout();plt.savefig(FIG/"importancia_mfcc.png",dpi=150);plt.close()

plt.figure(figsize=(6,4))
plt.hist(sc_o[y==0],bins=40,alpha=.6,density=True,label="Normal",color="#4C9F70")
plt.hist(sc_o[y==1],bins=40,alpha=.6,density=True,label="Anomalia",color="#C44E52")
plt.xlabel("Escore de anomalia (One-Class SVM)");plt.ylabel("Densidade")
plt.title("Distribuição dos escores de decisão (segmentos)");plt.legend()
plt.tight_layout();plt.savefig(FIG/"escores_ocsvm.png",dpi=150);plt.close()

acc_u={}
for tr,te in logo.split(X,y,g):
    rf2=RandomForestClassifier(n_estimators=400,class_weight="balanced",random_state=SEED).fit(X[tr],y[tr])
    acc_u[int(g[te][0])]=accuracy_score(y[te],rf2.predict(X[te]))
us=sorted(acc_u)
plt.figure(figsize=(6,4));plt.bar([f"AC{u:02d}" for u in us],[acc_u[u] for u in us],color="#5B7FA6")
plt.ylim(0,1);plt.ylabel("Acurácia (unidade fora do treino)")
plt.title("Desempenho por unidade — Floresta Aleatória (LOUO)")
plt.tight_layout();plt.savefig(FIG/"desempenho_unidade.png",dpi=150);plt.close()

# comparação de regimes
methods=["svm","random_forest","one_class_svm","baseline"]; labels=["SVM","Floresta Aleat.","One-Class SVM","Baseline"]
cross=[roc_auc_score(y,scores[m]) for m in methods]
within=[]
for m in methods:
    if m in ("svm","random_forest"):
        clf=make_pipeline(StandardScaler(),SVC(kernel="rbf",C=10,probability=True,class_weight="balanced")) if m=="svm" \
            else RandomForestClassifier(n_estimators=400,class_weight="balanced",random_state=SEED)
        sc=cross_val_predict(clf,X,y,groups=ids,cv=logo,method="predict_proba")[:,1]
        within.append(roc_auc_score(y,sc))
    else: within.append(np.nan)
x=np.arange(len(methods)); w=0.38
fig,ax=plt.subplots(figsize=(7,4.2))
ax.bar(x-w/2,within,w,label="Intra-distribuição (leave-one-recording-out)",color="#4C9F70")
ax.bar(x+w/2,cross,w,label="Entre unidades (leave-one-unit-out)",color="#C44E52")
ax.axhline(0.5,ls="--",lw=.8,color="grey")
ax.set_xticks(x);ax.set_xticklabels(labels);ax.set_ylim(0,1.05);ax.set_ylabel("AUC (nível de segmento)")
ax.set_title("Separabilidade acústica: intra-distribuição vs. entre unidades");ax.legend(loc="lower center",fontsize=8)
plt.tight_layout();plt.savefig(FIG/"regime_comparacao_auc.png",dpi=150);plt.close()

print("\nFiguras geradas em:", FIG.resolve())
