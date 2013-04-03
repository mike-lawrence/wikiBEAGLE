########
# Import all the modules we'll need
########

import numpy
import cPickle
import os
import shutil
import math
import time
import datetime


f = open('wikiBEAGLEdata/coList','r')
coList = cPickle.load(f)
f.close()

f = open('wikiBEAGLEdata/indexList','r')
indexList = cPickle.load(f)
f.close()		

numWords = len(indexList)

formList = numpy.memmap('wikiBEAGLEdata/form', mode='r+', dtype='float')
vectorLength = formList.size/numWords
formList.resize((numWords,vectorLength))

contextList = numpy.memmap('wikiBEAGLEdata/context', mode='w+', dtype='float', shape=(numWords,vectorLength))

fmax = 1.0*max([coList[word][word] for word,value in coList.items()])
ldfmax = math.log(1.0/fmax,2)

timeTaken = 0
wordsDone = 0
timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
os.system('clear')
print 'wikiBEAGLEcontext\n\nWords: '+str(numWords)+'\nProgress: '+str(int(round(wordsDone*1.0/numWords*100)))
lastUpdateTime = time.time()

for word,index in [[key,value] for key,value in indexList.items()]:
	for otherWord,times in [[key,value] for key,value in coList[word].items()]:
		if otherWord!=word:
			otherIndex = indexList[otherWord]
			otherFreq = coList[otherWord][otherWord]
			contextList[index] += formList[otherIndex]*times*(math.log(otherFreq/fmax,2)/ldfmax)
	wordsDone += 1
	if (time.time()-lastUpdateTime)>1:
		timeTaken += (time.time()-lastUpdateTime)
		lastUpdateTime = time.time()
		timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
		os.system('clear')
		print 'wikiBEAGLEcontext\n\nWords: '+str(numWords)+'\nProgress: '+str(int(round(wordsDone*1.0/numWords*100)))+'%\nTime: '+timeToPrint
	
del contextList
timeTaken += (time.time()-lastUpdateTime)
timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
os.system('clear')
print 'wikiBEAGLEcontext\n\nWords: '+str(numWords)+'\nTime taken: '+timeToPrint
