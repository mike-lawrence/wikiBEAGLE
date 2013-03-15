import numpy
import os
import shutil
import cPickle
import time
import datetime

def filterFileList(files,filter):
	i = 0
	while i < len(files):
		if files[i][0] in filter:
			trash = files.pop(i)
			del trash
		else:
			i = i + 1
	return files
	
	
if os.path.exists('wikiBEAGLEdata'):
	files = os.listdir('wikiBEAGLEdata')
	oldFiles = ('context' in files) and ('order' in files) and ('wordList' in files)
	files = filterFileList(files,['.','c','o','w'])
	if len(files)>1:
		startTime = time.time()
		print 'wikiBEAGLEcleaner\n\nCleaning...'
		if not oldFiles:
			file = files.pop(0)
			shutil.move('wikiBEAGLEdata/'+file+'/context','wikiBEAGLEdata/context')
			shutil.move('wikiBEAGLEdata/'+file+'/order','wikiBEAGLEdata/order')
			shutil.move('wikiBEAGLEdata/'+file+'/wordList','wikiBEAGLEdata/wordList')
			shutil.rmtree('wikiBEAGLEdata/'+file)
		f = open('wikiBEAGLEdata/wordList','r')
		wordList = cPickle.load(f)
		f.close()
		numWords = len(wordList)
		contextList = numpy.memmap('wikiBEAGLEdata/context', mode='r+', dtype='float')
		vectorLength = contextList.size/numWords
		contextList.resize((numWords,vectorLength))
		orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float')
		orderList.resize((numWords,vectorLength))
		os.system('clear')
		while len(files)>0:
			file = files.pop(0)
			os.system('clear')
			print 'wikiBEAGLEcleaner\n\nCleaning...'
			print '\n\nFiles left: '+str(len(files)+1)
			f = open('wikiBEAGLEdata/'+file+'/wordList','r')
			thisWordList = cPickle.load(f)
			f.close()
			thisWordNum = len(thisWordList)
			thisContextList = numpy.memmap('wikiBEAGLEdata/'+file+'/context', mode='r+', dtype='float')
			thisContextList.resize((thisWordNum,vectorLength))
			thisOrderList = numpy.memmap('wikiBEAGLEdata/'+file+'/order', mode='r+', dtype='float')
			thisOrderList.resize((thisWordNum,vectorLength))
			for j in thisWordList:
				if j in wordList:
					wordList[j]['frequency'] += thisWordList[j]['frequency']
					contextList[wordList[j]['index']] += thisContextList[thisWordList[j]['index']]
					orderList[wordList[j]['index']] += thisOrderList[thisWordList[j]['index']]
				else:
					wordList[j] = {}
					wordList[j]['frequency'] = thisWordList[j]['frequency']
					numWords = len(wordList)
					wordList[j]['index'] = numWords
					del contextList
					del orderList
					contextList = numpy.memmap('wikiBEAGLEdata/context', mode='r+', dtype='float', shape=(numWords,vectorLength))
					orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float', shape=(numWords,vectorLength))
					contextList[numWords-1] = thisContextList[thisWordList[j]['index']]
					orderList[numWords-1] = thisOrderList[thisWordList[j]['index']]
			del thisWordList,thisContextList,thisOrderList
			shutil.rmtree('wikiBEAGLEdata/'+file)
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nSaving...'
		tmp = open('wikiBEAGLEdata/wordList','wb')
		cPickle.dump(wordList,tmp)
		tmp.close()
		del contextList,orderList
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nCleaned.\n\nWords: '+str(len(wordList))+'  Tokens: '+str(sum(item['frequency'] for key,item in wordList.items()))+'  Time to aggregate: '+str(datetime.timedelta(seconds=round(time.time()-startTime)))
		
