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
	oldFiles = ('context' in files) and ('order' in files) and ('indexList' in files)
	files = filterFileList(files,['.','c','o','f','p','i'])
	if len(files)>1:
		startTime = time.time()
		print 'wikiBEAGLEcleaner\n\nCleaning...'
		if not oldFiles:
			file = files.pop(0)
			shutil.move('wikiBEAGLEdata/'+file+'/context','wikiBEAGLEdata/context')
			shutil.move('wikiBEAGLEdata/'+file+'/order','wikiBEAGLEdata/order')
			shutil.move('wikiBEAGLEdata/'+file+'/indexList','wikiBEAGLEdata/indexList')
			shutil.rmtree('wikiBEAGLEdata/'+file)
		f = open('wikiBEAGLEdata/indexList','r')
		indexList = cPickle.load(f)
		f.close()		
		numWords = len(indexList)
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
			f = open('wikiBEAGLEdata/'+file+'/indexList','r')
			thisIndexList = cPickle.load(f)
			f.close()
			thisNumWords = len(thisIndexList)
			thisContextList = numpy.memmap('wikiBEAGLEdata/'+file+'/context', mode='r+', dtype='float')
			thisContextList.resize((thisNumWords,vectorLength))
			thisOrderList = numpy.memmap('wikiBEAGLEdata/'+file+'/order', mode='r+', dtype='float')
			thisOrderList.resize((thisNumWords,vectorLength))
			for j in thisIndexList:
				if j in indexList:
					contextList[indexList[j]] += thisContextList[thisIndexList[j]]
					orderList[indexList[j]] += thisOrderList[thisIndexList[j]]
				else:
					numWords = len(indexList)+1
					indexList[j] = numWords
					del contextList
					del orderList
					contextList = numpy.memmap('wikiBEAGLEdata/context', mode='r+', dtype='float', shape=(numWords,vectorLength))
					orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float', shape=(numWords,vectorLength))
					contextList[numWords-1] = thisContextList[thisIndexList[j]]
					orderList[numWords-1] = thisOrderList[thisIndexList[j]]
			del thisIndexList,thisContextList,thisOrderList
			shutil.rmtree('wikiBEAGLEdata/'+file)
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nSaving...'
		tmp = open('wikiBEAGLEdata/indexList','wb')
		cPickle.dump(indexList,tmp)
		tmp.close()
		del contextList,orderList
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nCleaned. Time to aggregate: '+str(datetime.timedelta(seconds=round(time.time()-startTime)))+'\n\n'
		
