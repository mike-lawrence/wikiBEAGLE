import numpy
import os
import cPickle
import time
import datetime
if os.path.exists('wikiBeagleData'):
	files = os.listdir('wikiBeagleData')
	if len(files)>1:
		os.system('clear')
		startTime = time.time()
		print 'wikiBEAGLEcleaner\n\nCleaning...'
		file = files.pop()
		tmp = open('wikiBeagleData/'+file,'rb')
		freqList,formList,contextList,orderList = cPickle.load(tmp)
		tmp.close()
		os.remove('wikiBeagleData/'+file)
		while len(files)>0:
			file = files.pop()
			os.system('clear')
			print 'wikiBEAGLEcleaner\n\nCleaning...'
			print '\n\nFiles left: '+str(len(files)+1)
			tmp = open('wikiBeagleData/'+file,'rb')
			freqList2,formList2,contextList2,orderList2 = cPickle.load(tmp)
			tmp.close()
			os.remove('wikiBeagleData/'+file)
			for j in freqList2:
				if j in freqList:
					freqList[j] = freqList[j] + freqList2[j]
					formList[j] = formList[j] + formList2[j]
					contextList[j] = contextList[j] + contextList2[j]
					orderList[j] = orderList[j] + orderList2[j]
				else:
					freqList[j] = freqList2[j]
					formList[j] = formList2[j]
					contextList[j] = contextList2[j]
					orderList[j] = orderList2[j]
			del freqList2,formList2,contextList2,orderList2
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nSaving...'
		tmp = open('wikiBeagleData/0','wb')
		cPickle.dump([freqList,formList,contextList,orderList],tmp)
		tmp.close()
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nCleaned.\n\nWords: '+str(len(freqList))+'  Tokens: '+str(sum(freqList.values()))+'  Time to aggregate: '+str(datetime.timedelta(seconds=round(time.time()-startTime)))
		