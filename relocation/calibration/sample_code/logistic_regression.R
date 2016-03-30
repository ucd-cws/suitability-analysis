## Logistic Regression/BRT/Random Forests
## R.Peek
## Test modeling script to look at binary response of towns moving or not

# Load Libraries & Data ---------------------------------------------------

library(readr)
library(dplyr)

setwd("C:/Users/dsx.AD3/Code/FloodMitigation")

## read in data
dat<-read_csv("relocation/calibration/fake_data.csv")
str(dat) # data structure
names(dat) # col names

# 1. USING MCELREATHS MODEL FRAMEWORK: LOGISTIC REGRESSION -----------------
library(rethinking) # this is a big package and requires RStan, ask Ryan for help to install

df1<-dat

# using mcelreath's rethinking package we need to coerce factors/characters to numeric
df1$dom_land_numeric<-coerce_index(df1$dominant_land_cover) # make numeric
df1$chosen<-as.numeric(df1$chosen)

# subset to the dataframe for the model
df1_sub<-select(df1, id, chosen, min_elevation_change:mean_floodplain_distance_change, dom_land_numeric)

# Scale and center function (to avoid attributing issues associated with "scale()" function)
scale_center<-function(x){
  y<-(x - mean(x)) / sd(x)
  return(y)
}

# use dplyr to scale all data at once
names(df1_sub)

df1_s<-df1_sub %>%
  group_by(id, chosen) %>% 
  select(min_elevation_change:dom_land_numeric) %>% 
  sapply(FUN =scale_center) %>% #applies to all cols
  cbind(df1_sub[,c(1:2)]) %>% # rebind the original ID column 
  as.data.frame()
dim(df1)
df1_s<-df1_s[,c(14:15,3:13)] # drop the "scaled" ID column and chosen and re-add
s(df1_s)

# 1a. BUILD SOME MODELS -------------------------------------------------------

names(df1_s)

# rename outcomes
dlist <- list(
  chosen=df1_s$chosen,
  name=df1_s$id,
  min_elev_delt=df1_s$min_elevation_change,
  max_elev_delt=df1_s$max_elevation_change,
  mean_elev_delt=df1_s$mean_elevation_change,
  cent_elev=df1_s$centroid_elevation,
  minslope_delt=df1_s$min_slope_change,
  maxslope_delt=df1_s$max_slope_change,
  meanslope_delt=df1_s$mean_slope_change,
  min_floodist_delt=df1_s$min_floodplain_distance_change,
  max_floodist_delt=df1_s$max_floodplain_distance_change,
  mean_floodist_delt=df1_s$mean_floodplain_distance_change,
  dom_land=df1_s$dom_land_numeric
)

# basic logistic regression, fixed intercept and slope
m01 <- map(
  alist(
    chosen ~ dbinom( 1 , p ) ,
    logit(p) <- a + bminE*min_elev_delt +bmaxE*max_elev_delt +bavgE*mean_elev_delt +
      bcentE*cent_elev + bminSl*minslope_delt + bmaxSl*maxslope_delt + 
      bavgSl*meanslope_delt + bminFld*min_floodist_delt + bmaxFld*max_floodist_delt +
      bavgFld*mean_floodist_delt + bLnd*dom_land,
    a ~ dnorm(0,10),
    c(bminE,bmaxE,bavgE,bcentE,bminSl,bmaxSl,bavgSl,bminFld,bmaxFld,bavgFld,bLnd) ~ dnorm(0,10)
  ),
  data=dlist, start=list(a=0, bminE=0, bmaxE=0, bavgE=0, bcentE=0, bminSl=0,
                         bmaxSl=0,bavgSl=0,bminFld=0,bmaxFld=0,bavgFld=0,bLnd=0))

# summarize
precis(m01) # this gives the scores in table format
plot(precis(m01)) # this give a plot of the table

## looks like bminElevation is strong (postive) and bmaxElev is strong negative predictor
## minimum flood distance also appears to have negative relationship with town moving. Not strong though.

# summarize
post01 <- extract.samples(m01) # extract samples from model posterior
par(mfrow=c(1,1))
dens( post01$bminE, show.HPDI = 0.95,col="orange", show.zero = T, xlim=c(-4,4)) # plot distribution of samples for minE
# steeper curve means more values are less variable, and might be better indicator?
dens( post01$bmaxE, show.HPDI = 0.95, col="red",show.zero = T, add = T) # plot distribution of samples for maxE
# pretty wide base.
dens( post01$bminFld, show.HPDI = 0.95, col="blue",show.zero = T, add = T) # plot distribution of samples for maxE

# RStan fit: same model as above but with MCMC 
m02 <- map2stan(
  alist(
    chosen ~ dbinom( 1 , p ) ,
    logit(p) <- a + bminE*min_elev_delt +bmaxE*max_elev_delt +bavgE*mean_elev_delt +
      bcentE*cent_elev + bminSl*minslope_delt + bmaxSl*maxslope_delt + 
      bavgSl*meanslope_delt + bminFld*min_floodist_delt + bmaxFld*max_floodist_delt +
      bavgFld*mean_floodist_delt + bLnd*dom_land,
    a ~ dnorm(0,10),
    c(bminE,bmaxE,bavgE,bcentE,bminSl,bmaxSl,bavgSl,bminFld,bmaxFld,bavgFld,bLnd) ~ dnorm(0,10)
  ),
  data=dlist, chains=2, cores=2)

# summarize
precis(m02)
plot(precis(m02))

plot(m02) # see how MCMC chains did

# compare models
coeftab(m01,m02)
dev.off() # just to clear the plots
plot(coeftab(m01,m02))

# show WAIC for models
compare(m01,m02) # amazing warning message here, ignore
plot(compare(m01,m02))

# now with varying intercepts (towns can vary independently, and are different)
m03 <- map2stan(
  alist(
    chosen ~ dbinom( 1 , p ) ,
    logit(p) <- a + aj[name] + bminE*min_elev_delt +bmaxE*max_elev_delt +bavgE*mean_elev_delt +
      bcentE*cent_elev + bminSl*minslope_delt + bmaxSl*maxslope_delt + 
      bavgSl*meanslope_delt + bminFld*min_floodist_delt + bmaxFld*max_floodist_delt +
      bavgFld*mean_floodist_delt + bLnd*dom_land,
    aj[name] ~ dnorm(0,sigma_town),
    a ~ dnorm(0,10),
    c(bminE,bmaxE,bavgE,bcentE,bminSl,bmaxSl,bavgSl,bminFld,bmaxFld,bavgFld,bLnd) ~ dnorm(0,10),
    sigma_town ~ dcauchy(0,1)
  ),
  data=dlist, chains=2, cores=2)

# pairs(m03)
coeftab(m02,m03) # compare MCMC models only
plot(coeftab(m02,m03))

plot(m03)
plot(precis(m03,depth = 1))


# show WAIC for models
compare(m02,m03)
plot(compare(m02,m03))

# reduced version 
m04 <- map2stan(
  alist(
    chosen ~ dbinom( 1 , p ) ,
    logit(p) <- a + aj[name] + bminE*min_elev_delt + bmaxE*max_elev_delt +
      bmaxSl*maxslope_delt + bavgSl*meanslope_delt +  
      bmaxFld*max_floodist_delt + bLnd*dom_land,
    aj[name] ~ dnorm(0,sigma_town),
    a ~ dnorm(0,10),
    c(bminE, bmaxE, bmaxSl, bavgSl, bmaxFld, bLnd) ~ dnorm(0,10),
    sigma_town ~ dcauchy(0,1)
  ),
  data=dlist, chains=2, cores=2)

plot(precis(m04))

compare(m02,m03, m04)
plot(compare(m02,m03, m04))

# 2. Boosted regression Trees ---------------------------------------------

library(gbm)

# subset to the dataframe for the model
df2_s<-dplyr::select(df1_s, -id)
names(df2_s)

# subset to the dataframe for the model
df2_s<-as.data.frame(df2_s)
head(df2_s)

gbm1 <-
  gbm(chosen~.,
      data=df2_s,
      distribution="bernoulli",
      n.trees=5000,
      shrinkage=0.01,       # shrinkage or learning rate, 0.001 to 0.1 usually work
      interaction.depth=2,  # 1: additive model, 2: two-way interactions, etc.
      bag.fraction = 0.5,   # subsampling fraction, 0.5 is probably best
      train.fraction = 0.5, # fraction of data for training, first train.fraction*N used for training
      n.minobsinnode = 2,   # minimum total weight needed in each node
      cv.folds = 3,         # do 3-fold cross-validation
      keep.data=TRUE,       # keep a copy of the dataset with the object
      verbose=TRUE,
      n.cores=1)

gbm1 # best number of trees=128?

# look at results of relative influence
relative.influence(gbm1,sort. = T)

# confusion table (confusing!!)
confusionMatrix(predict(gbm1, df2_s, n.trees = 128) > 0, df2_s$chosen > 0)
confusionMatrix(predict(gbm1, df2_s, n.trees = 1000) > 0, df2_s$chosen > 0)

# summary of model
print(gbm1)

# barplots of relative influence  (in pretty blue)
par(mar=c(5,10,2,1), las=2)
relvars<-summary(gbm1,method=permutation.test.gbm) # different method
relvars_ri<-summary(gbm1, method=relative.influence) # main method

# barplots of influence to export
svg(filename="towns_rel_inf_BRT.svg", width=8, height=6)
par(mar=c(5,10,3,1), las=2)
barplot(rev(relvars_ri$rel.inf), names.arg = rev(relvars_ri$var), col=rev(gray.colors(22)), 
        horiz = T, angle = 30, xlab = "relative influence", cex.names = 0.7)
title("Relative Influence of Variables: BRT")
dev.off()

# 3. REGRESSION WITH CARET ------------------------------------------------

library(caret)

# orig data
df3 <- dat

# change some cols
df3$dom_land_numeric<-as.numeric(as.factor(df3$dominant_land_cover)) # make numeric
df3$chosen_binary<-as.numeric(df3$chosen) # recode since T/F causes problems later
df3$chosen<-as.factor(ifelse(df3$chosen==TRUE, "yes", "no")) # recode since T/F causes problems later
str(df3)
summary(df3)

# subset to the dataframe for the model
df3_sub<-as.data.frame(dplyr::select(df3, chosen, chosen_binary,
                              min_elevation_change:mean_floodplain_distance_change, 
                              dom_land_numeric))
str(df3_sub)

# create training data set
inTrain <- createDataPartition(y = df3_sub$chosen_binary, ## the outcome data are needed
                               p = .5, ## The percentage of data in the training set
                               list = FALSE) ## The format of the results

# for factors
inTrain2 <- createDataPartition(y = df3_sub$chosen, ## the outcome data are needed
                               p = .5, ## The percentage of data in the training set
                               list = FALSE) ## The format of the results

# make datasets
train_bin <- df3_sub[ inTrain,-1] # drop the chosen factor col
test_bin <- df3_sub[-inTrain,-1] # drop the chosen facor col

train <- df3_sub[ inTrain2,-2] # drop the chosen factor col
test <- df3_sub[-inTrain2,-2] # drop the chosen facor col
head(train)
nrow(test_bin)

# 3a. Classic Logistic Regression with CARET -------------------------------

# Use a classic logistic regression, model with all vars
glm.fit <- glm(chosen_binary ~ min_elevation_change + max_elevation_change + mean_elevation_change + 
              centroid_elevation + min_slope_change + max_slope_change + mean_slope_change +
              min_floodplain_distance_change + max_floodplain_distance_change + 
              mean_floodplain_distance_change + dom_land_numeric, 
            data=train_bin, family="binomial")

summary(glm.fit)

# 3b. GLM Boost with CARET ------------------------------------------------

# this will perform variable selection unlike plain glm

set.seed(2014) # so repeatable

# set some model parameters
fitControl <- trainControl(method = "cv",
                           number = 5,
                           repeats = 10,
                           ## Estimate class probabilities
                           classProbs = TRUE,
                           ## Evaluate performance using 
                           ## the following function
                           summaryFunction = twoClassSummary)


glmBoost <- train(chosen ~ ., data=train, method = "glmboost", 
                   tuneLength=5,center=T,
                   family=Binomial(link = c("logit")))



varImp(glmBoost)
plot(glmBoost)
# need library(pROC)
pred.glmBoost <- as.vector(predict(glmBoost, newdata=test, type="prob")[,"yes"])
(roc.glmBoost <- pROC::roc(test$chosen, pred.glmBoost))
(auc.glmBoost <- pROC::auc(roc.glmBoost))
plot(roc.glmBoost)

# see variable importance, uncomment the svg & dev.off to save a plot
#svg("var_importance_glmboost.svg",width = 8, height = 6)
plot(varImp(glmBoost))
#dev.off()

# 3c. RANDOM FOREST WITH CARET  --------------------------------------------

# set some model parameters
fitControl <- trainControl(method = "repeatedcv",
                           number = 5,
                           repeats = 10,
                           ## Estimate class probabilities
                           classProbs = TRUE,
                           ## Evaluate performance using 
                           ## the following function
                           summaryFunction = twoClassSummary)

set.seed(2014)

# Random Forest
set.seed(2014)

rfModel <- train(chosen ~ ., data=train, method = "rf", metric="ROC", trControl = fitControl, verbose=FALSE, tuneLength=5)
pred.rfModel <- as.vector(predict(rfModel, newdata=test, type="prob")[,"yes"])
(roc.rfModel <- pROC::roc(test$chosen, pred.rfModel))
(auc.rfModel <- pROC::auc(roc.rfModel))
plot(rfModel)

# see variable importance, uncomment the svg & dev.off to save a plot
#svg("var_importance_RF.svg",width = 8, height = 6)
plot(varImp(rfModel))
#dev.off()


# PICK BEST MODEL ---------------------------------------------------------

test.auc <- data.frame(model=c("glmboost","rForest"), auc=c(auc.glmBoost, auc.rfModel))
test.auc <- test.auc[order(test.auc$auc, decreasing=TRUE),]
test.auc$model <- factor(test.auc$model, levels=test.auc$model)
test.auc # looks like RF is best

