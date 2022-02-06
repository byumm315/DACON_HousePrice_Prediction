# -*- coding: utf-8 -*-
"""DACON_집값예측경진대회.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nHkZEJKoEzHE2ImXkY3XVqWeWoBn-5Qm
"""

import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder

# 다운받은 csv를 pandas의 DataFrame 형식으로 불러옵니다.
from google.colab import drive
drive.mount('/content/drive')
import pandas as pd
data=pd.read_csv('/content/drive/MyDrive/housing/train.csv',sep=',',encoding="cp949")
test=pd.read_csv('/content/drive/MyDrive/housing/test.csv',sep=',',encoding="cp949")

# id 는 제외하고 분석합니다.
data = data.drop('id', axis=1)
test = test.drop('id', axis=1)

data= data.drop_duplicates()#중복값제거
data.loc[254, 'Garage Yr Blt'] = 2007 #이상한값 변경

# 품질 관련 변수 → 숫자로 매핑
qual_cols = data.dtypes[data.dtypes == np.object].index
def label_encoder(df_, qual_cols):
  df = df_.copy()
  mapping={
      'Ex':5, 'Gd':4, 'TA':3, 'Fa':2, 'Po':1
  }
  for col in qual_cols :
    df[col] = df[col].map(mapping)
  return df

data = label_encoder(data, qual_cols)
test = label_encoder(test, qual_cols)

#Feature Engineering
def feature_eng(data_):
  data = data_.copy()
  data['Overall Qual^2']=data['Overall Qual']*data['Overall Qual']
  data['Overall Qual^3']=data['Overall Qual']*data['Overall Qual']*data['Overall Qual']
  data['Bath*Area']=data['Full Bath']*data['Gr Liv Area'] 
  data['base*1st']=data['Total Bsmt SF']*data['1st Flr SF']
  data['Gr Liv Area^2']=data['Gr Liv Area']*data['Gr Liv Area']
  data['Gr Liv Area^3']=data['Gr Liv Area']*data['Gr Liv Area']*data['Gr Liv Area']
  data['Cars*Area']=data['Garage Cars']*data['Garage Area']
  data['Year Gap Remod'] = data['Year Remod/Add'] - data['Year Built']
  data['Car Area'] = data['Garage Area']/data['Garage Cars']
  data['New_Year Built']=2022-data['Year Built']
  data['New_Year Remod/Add']=2022-data['Year Remod/Add']
  data['New_Garage Yr Blt']=2022-data['Garage Yr Blt']
  data['2nd flr SF'] = data['Gr Liv Area'] - data['1st Flr SF']
  data['2nd flr'] = data['2nd flr SF'].apply(lambda x : 1 if x > 0 else 0)
  data['Total SF'] = data[['Gr Liv Area',"Garage Area", "Total Bsmt SF"]].sum(axis=1)
  data['Sum Qual'] = data[["Exter Qual", "Kitchen Qual", "Overall Qual"]].sum(axis=1)
  data['Garage InOut'] = data.apply(lambda x : 1 if x['Gr Liv Area'] != x['1st Flr SF'] else 0, axis=1)
  return data
train = feature_eng(data)
test = feature_eng(test)

train=train.drop(['Year Built','Year Remod/Add','Garage Yr Blt'],axis=1)
test=test.drop(['Year Built','Year Remod/Add','Garage Yr Blt'],axis=1)

!pip3 install ngboost

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from ngboost import NGBRegressor
from sklearn.metrics import make_scorer
from sklearn.model_selection import KFold

# 평가 기준 정의
def NMAE(true, pred):
    mae = np.mean(np.abs(true-pred))
    score = mae / np.mean(np.abs(true))
    return score

nmae_score = make_scorer(NMAE, greater_is_better=False)
kf = KFold(n_splits = 10, random_state =42, shuffle = True)#42

X = train.drop(['target'], axis = 1)
y = np.log1p(train.target)

target = test[X.columns]

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Ridge
rg_pred = np.zeros(target.shape[0])
rg_val = []
for n, (tr_idx, val_idx) in enumerate(kf.split(X, y)) :
    print(f'{n + 1} FOLD Training.....')
    tr_x, tr_y = X.iloc[tr_idx], y.iloc[tr_idx]
    val_x, val_y = X.iloc[val_idx], np.expm1(y.iloc[val_idx])
    
    rg = Ridge()
    rg.fit(tr_x, tr_y)
    
    val_pred = np.expm1(rg.predict(val_x))
    val_nmae = NMAE(val_y, val_pred)
    rg_val.append(val_nmae)
    print(f'{n + 1} FOLD NMAE = {val_nmae}\n')
    
    target_data = Pool(data = target, label = None)
    fold_pred = rg.predict(target) / 10
    rg_pred += fold_pred
print(f'10FOLD Mean of NMAE = {np.mean(rg_val)} & std = {np.std(rg_val)}')

# GradientBoostingRegressor
gbr_pred = np.zeros(target.shape[0])
gbr_val = []
for n, (tr_idx, val_idx) in enumerate(kf.split(X, y)) :
    print(f'{n + 1} FOLD Training.....')
    tr_x, tr_y = X.iloc[tr_idx], y.iloc[tr_idx]
    val_x, val_y = X.iloc[val_idx], np.expm1(y.iloc[val_idx])
    
    gbr = GradientBoostingRegressor(random_state = 43, max_depth = 4, learning_rate = 0.03, n_estimators = 1000) 
    gbr.fit(tr_x, tr_y)
    
    val_pred = np.expm1(gbr.predict(val_x))
    val_nmae = NMAE(val_y, val_pred)
    gbr_val.append(val_nmae)
    print(f'{n + 1} FOLD NMAE = {val_nmae}\n')
    
    fold_pred = gbr.predict(target) / 10
    gbr_pred += fold_pred
print(f'10FOLD Mean of NMAE = {np.mean(gbr_val)} & std = {np.std(gbr_val)}')

# RandomForestRegressor
rf_pred = np.zeros(target.shape[0])
rf_val = []
for n, (tr_idx, val_idx) in enumerate(kf.split(X, y)) :
    print(f'{n + 1} FOLD Training.....')
    tr_x, tr_y = X.iloc[tr_idx], y.iloc[tr_idx]
    val_x, val_y = X.iloc[val_idx], np.expm1(y.iloc[val_idx])
    
    rf = RandomForestRegressor(random_state = 42, criterion = 'absolute_error')#50
    rf.fit(tr_x, tr_y)
    
    val_pred = np.expm1(rf.predict(val_x))
    val_nmae = NMAE(val_y, val_pred)
    rf_val.append(val_nmae)
    print(f'{n + 1} FOLD NMAE = {val_nmae}\n')
    
    fold_pred = rf.predict(target) / 10
    rf_pred += fold_pred
print(f'10FOLD Mean of NMAE = {np.mean(rf_val)} & std = {np.std(rf_val)}')

# NGBRegressor
ngb_pred = np.zeros(target.shape[0])
ngb_val = []
for n, (tr_idx, val_idx) in enumerate(kf.split(X, y)) :
    print(f'{n + 1} FOLD Training.....')
    tr_x, tr_y = X.iloc[tr_idx], y.iloc[tr_idx]
    val_x, val_y = X.iloc[val_idx], np.expm1(y.iloc[val_idx])
    
    ngb = NGBRegressor(random_state = 42, n_estimators = 1000, verbose = 0, learning_rate = 0.03) #1000
    ngb.fit(tr_x, tr_y, val_x, val_y, early_stopping_rounds = 300)
    
    val_pred = np.expm1(ngb.predict(val_x))
    val_nmae = NMAE(val_y, val_pred)
    ngb_val.append(val_nmae)
    print(f'{n + 1} FOLD NMAE = {val_nmae}\n')
    
    target_data = Pool(data = target, label = None)
    fold_pred = ngb.predict(target) / 10
    ngb_pred += fold_pred
print(f'10FOLD Mean of NMAE = {np.mean(ngb_val)} & std = {np.std(ngb_val)}')

# 검증 성능 확인하기
val_list = [rg_val, gbr_val, rf_val, ngb_val]
for val in val_list :
  print("{:.8f}".format(np.mean(val)))

# submission 파일에 입력
sub=pd.read_csv('/content/drive/MyDrive/housing/sample_submission.csv',sep=',',encoding="cp949")
sub['target'] = np.expm1((ngb_pred + rf_pred + rg_pred + gbr_pred) / 4)
sub['target']

sub.to_csv('dacon_file.csv',index=False)