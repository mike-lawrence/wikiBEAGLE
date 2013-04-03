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
	oldFiles = ('coList' in files) and ('order' in files) and ('indexList' in files)
	files = filterFileList(files,['.','c','o','f','p','i','w'])
	if len(files)>1:
		startTime = time.time()
		print 'wikiBEAGLEcleaner\n\nCleaning...'
		if not oldFiles:
			file = files.pop(0)
			shutil.move('wikiBEAGLEdata/'+file+'/coList','wikiBEAGLEdata/coList')
			shutil.move('wikiBEAGLEdata/'+file+'/form','wikiBEAGLEdata/form')
			shutil.move('wikiBEAGLEdata/'+file+'/order','wikiBEAGLEdata/order')
			shutil.move('wikiBEAGLEdata/'+file+'/indexList','wikiBEAGLEdata/indexList')
			shutil.rmtree('wikiBEAGLEdata/'+file)
		f = open('wikiBEAGLEdata/indexList','r')
		indexList = cPickle.load(f)
		f.close()		
		f = open('wikiBEAGLEdata/coList','r')
		coList = cPickle.load(f)
		f.close()		
		numWords = len(indexList)
		orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float')
		vectorLength = orderList.size/numWords
		orderList.resize((numWords,vectorLength))
		formList = numpy.memmap('wikiBEAGLEdata/form', mode='r+', dtype='float')
		formList.resize((numWords,vectorLength))
		os.system('clear')
		while len(files)>0:
			file = files.pop(0)
			if 'indexList' in os.listdir('wikiBEAGLEdata/'+file):
				os.system('clear')
				print 'wikiBEAGLEcleaner\n\nCleaning...'
				print '\n\nFiles left: '+str(len(files)+1)
				f = open('wikiBEAGLEdata/'+file+'/indexList','r')
				thisIndexList = cPickle.load(f)
				f.close()
				f = open('wikiBEAGLEdata/'+file+'/coList','r')
				thisCoList = cPickle.load(f)
				f.close()
				thisNumWords = len(thisIndexList)
				thisOrderList = numpy.memmap('wikiBEAGLEdata/'+file+'/order', mode='r+', dtype='float')
				thisOrderList.resize((thisNumWords,vectorLength))
				thisFormList = numpy.memmap('wikiBEAGLEdata/'+file+'/form', mode='r+', dtype='float')
				thisFormList.resize((thisNumWords,vectorLength))
				for j in thisIndexList:
					if j in indexList:
						orderList[indexList[j]] += thisOrderList[thisIndexList[j]]
						for k in thisCoList[j]:
							if k in coList[j]:
								coList[j][k] += thisCoList[j][k]
							else:
								coList[j][k] = thisCoList[j][k]
					else:
						numWords = len(indexList)+1
						indexList[j] = numWords-1
						del orderList,formList
						orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float', shape=(numWords,vectorLength))
						orderList[numWords-1] = thisOrderList[thisIndexList[j]]
						formList = numpy.memmap('wikiBEAGLEdata/form', mode='r+', dtype='float', shape=(numWords,vectorLength))
						formList[numWords-1] = thisFormList[thisIndexList[j]]
						coList[j] = thisCoList[j]					
				del thisIndexList,thisCoList,thisOrderList,thisFormList
				shutil.rmtree('wikiBEAGLEdata/'+file)
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nSaving...'
		tmp = open('wikiBEAGLEdata/indexList','wb')
		cPickle.dump(indexList,tmp)
		tmp.close()
		tmp = open('wikiBEAGLEdata/coList','wb')
		cPickle.dump(coList,tmp)
		tmp.close()
		del orderList,formList
		os.system('clear')
		print 'wikiBEAGLEcleaner\n\nCleaned. Time to aggregate: '+str(datetime.timedelta(seconds=round(time.time()-startTime)))+'\n\n'
		
