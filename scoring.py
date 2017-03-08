import numpy as np
import pandas as pd
import logging
from os.path import splitext

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
cv = 5

def cv_accuracy_plot(clfs, features, labels, cpdnames, model_names, args):
    from scipy import interp
    from sklearn.cross_validation import StratifiedKFold
    from sklearn.metrics import roc_curve, auc
 
    docking_score = features[:, -1]
    if args.use_docking_score:
        X = features
    else:
        X = features[:, :-1]
    y = labels

    #n-fold cv, make ROC for each classifier
    cvs = StratifiedKFold(y, n_folds=cv)


    for clf, name in zip(clfs, model_names):
        mean_tpr = 0.0
        mean_fpr = np.linspace(0, 1, 100)
        aucs = []
        
        #feature importance for RandomForest
        mean_importances = np.array([0.0 for _ in range(X.shape[1])])
        result_file = open("result_cpd.csv", "w")
        scores = np.array([])

        for i, (train, test) in enumerate(cvs):
            probas_ = clf.fit(X[train], y[train]).predict_proba(X[test])
            cpdnames_ = cpdnames[test]

            #record scores, having bug
            score = np.hstack((cpdnames_, probas_[:, 1]))
            scores = np.concatenate([scores, score], axis=0)
            
            # Compute ROC curve and area the curve
            fpr, tpr, thresholds = roc_curve(y[test], probas_[:, 1])
            tpr = [0.0] + tpr
            fpr = [0.0] + fpr
            mean_tpr += interp(mean_fpr, fpr, tpr)
            mean_tpr[0] = 0.0
            roc_auc = auc(fpr, tpr)
            aucs.append(roc_auc)
            plt.plot(fpr, tpr, lw=1, label='%s fold %d (AUC = %0.3f)'
                     % (name, i, roc_auc))
            
            # get feature importance
            if "RF" in name:
                try:
                    mean_importances += clf.feature_importances_
                except:
                    import traceback
                    traceback.print_exc()
                    logger.debug("feature importance is not available. Not Forests?")

        mean_tpr /= len(cvs)
        mean_tpr[-1] = 1.0
        mean_auc = auc(mean_fpr, mean_tpr)
        plt.plot(mean_fpr, mean_tpr, 'k--',
                 label='Mean (AUC = %0.2f)' % mean_auc, lw=1)
        print(scores)
        np.savetxt("result"+name+"_cpd.csv", scores, fmt="%s", delimiter=",")
        if "RF" in name:
            mean_importances /= len(cvs)

        
    #glide score, reverse order
    fpr, tpr, thresholds = roc_curve(y, docking_score*(-1))
    tpr = [0.0] + tpr
    fpr = [0.0] + fpr
    docking_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, 'r--', lw=1, label='Glide SP (AUC = %0.3f)' % docking_auc)
    
    plt.plot([0, 1], [0, 1], '--', lw=1, color=(0.6, 0.6, 0.6), label='Random')

    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC: '+args.title)
    plt.legend(loc="lower right", fontsize=9)
    outputfile = splitext(args.output)[0]+".png"
    plt.savefig(outputfile)

    aucs.append(mean_auc)
    aucs.append(docking_auc)
    aucs = np.array(aucs)
    np.savetxt(args.output, aucs.T, delimiter=",", fmt="%.3f")    


    plt.clf()

    #feature importance for RF
    if any([("RF" in name) for name in model_names]):
        outputfile = splitext(args.output)[0]+".importance"
        np.savetxt(outputfile, mean_importances, delimiter=",")
        
    return aucs


def scoring_param_search(title, label_data, features, args):

    if args.zeroneg:
        y = np.array([1 if x>0 else 0 for x in label_data])    
    else:
        y = label_data

    docking_score = features[:, -1]
    if args.use_docking_score:
        X = features
    else:
        X = features[:, :-1]

    from sklearn.cross_validation import StratifiedKFold
    skf = StratifiedKFold(y, cv)

    if args.model == "RF":
        #Random Forest, Grid search by CV
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=1000, criterion='gini')
        maxf = min(31, len(X[0, :]))
        param_grid = [{'max_features': list(range(2, maxf))+['auto']}]

    elif args.model == "SVM":
        from sklearn.svm import SVC
        model = SVC(C=10, kernel="rbf", degree=3, gamma=0.1, cache_size=1000)
        param_grid = [{""}]

    from sklearn import grid_search
    clf = grid_search.GridSearchCV(model, param_grid, cv=skf,
                                   scoring='roc_auc', n_jobs=args.nprocs)
    clf.fit(X, y)

    #evaluate scores
    grid_scores = [["max_features", "mean_score_CV", "std_CV"]]
    for params, mean_score, all_scores in clf.grid_scores_:
        grid_scores.append([params['max_features'], 
                            mean_score, all_scores.std()])
    grid_scores_df = pd.DataFrame(grid_scores[1:],
                                  columns=grid_scores[0])
    print(grid_scores_df)

    #output
    grid_scores_df.to_csv(args.output, delimiter=",")
    
    print(clf.best_params_, clf.best_score_)
    score = clf.best_estimator_.predict_proba(X)[:,1]

    rank = np.argsort(score)[::-1][:args.propose]
    cpdname = title[rank]
    score = score[rank]
    label = y[rank]

    result = np.array(zip(cpdname, score, label))
    #print(result)
    result = np.dstack((cpdname, score, label))

    #test
    #np.savetxt(outputfile, result, fmt="%s", delimiter=",")
    logger.info('Saved SIEVE-Score.')

    return cpdname, score, label

def scoring_eval(title, label_data, features, args):

    outputfile = args.output

    if args.zeroneg:
        labels = np.array([1 if x>0 else 0 for x in label_data])    
    else:
        #TODO
        logger.info("not zeroneg is not inplemented here.")
        raise NotImplementedError()

    if args.model == "RF":
        from sklearn.ensemble import RandomForestClassifier as RFC
        clfs = [RFC(n_estimators=1000, criterion='gini', max_features=6)]
        names = ['SIEVE-Score RF']

    elif args.model == "SVM":
        from sklearn.svm import SVC
        clfs = [SVC(C=10, kernel="rbf", degree=3, gamma=0.1,
                    cache_size=1000, probability=True)]
        names = ['SIEVE-Score SVM']

    mean_auc = cv_accuracy_plot(clfs, features, labels, title, names, args)

    #TEST
    print("Finished in scoring_eval.")
    quit()

    score = clfs[0].predict_proba(features)[:,1]

    rank = np.argsort(score)[::-1][:args.propose]
    cpdname = title[rank]
    score = score[rank]
    label = labels[rank]

    result = np.array(zip(cpdname, score, label))
    #print(result)
    result = np.dstack((cpdname, score, label))

    #test
    #np.savetxt(outputfile, result, fmt="%s", delimiter=",")
    logger.info('Saved SIEVE-Score.')

    return cpdname, score, label

def scoring_compareSVMRF(title, label_data, features, args):
    outputfile = args.output

    if args.zeroneg:
        labels = np.array([1 if x>0 else 0 for x in label_data])
    else:
        #TODO                                                                                                                                  
        logger.info("not zeroneg is not inplemented here.")
        raise NotImplementedError()

    from sklearn.ensemble import RandomForestClassifier as RFC
    from sklearn.svm import SVC

    clfs = [SVC(C=10, kernel="rbf", degree=3, gamma=0.1, cache_size=1000, probability=True),
            RFC(n_estimators=1000, criterion='gini', max_features=6)]
    names = ['SVM', 'RF']

    mean_auc = cv_accuracy_plot(clfs, features, labels, names, args)

    logger.info('Finished to compare')
    quit()
