import sys

if len(sys.argv)==1:
	numCores = 1
else:
	numCores = int(sys.argv[1])

#set the length of the vectors
vectorLength = 2**10

#set the amount of free memory (%) below which cleaning will take place
lowMemCleanPoint = 10

import datetime
import multiprocessing
import signal
import time
import string
import re
import numpy
import cPickle
import urllib2
import os
import shutil

#define a function to check the available memory
def checkFreeMemory():
	m = os.popen('ps -axmo %mem')
	m = m.readlines()
	m = m[1:-1]
	for i in range(len(m)): m[i] = m[i].replace('\n','')
	for i in range(len(m)): m[i] = m[i].replace(' ','')
	for i in range(len(m)): m[i] = m[i].replace('.','')
	for i in range(len(m)): m[i] = int(m[i])
	free = 100-(sum(m)/10)
	return free


#define a function to delete some html in text
def delHtml(text):
	done = False
	while not done:
		if '<' in text:
			i = 0
			while text[i]!='<':
				i += 1
			if '>' in text:
				j = i
				while text[j]!='>':
					j += 1
				text = text[0:i]+text[(j+1):]
			else:
				done = True
		else:
			done = True
	return(text)


#define a function that cleans up a page of text from wikipedia, returning a list of paragraphs
def cleanPage(page):
	pageLines = page.readlines()
	pageLinesFinal = []
	for thisPageLine in pageLines:
		if thisPageLine[0:3]=='<p>':
			line = delHtml(thisPageLine)
			line = line.replace('\n','')
			line = line.lower() #convert to lowercase
			line = ''.join(re.findall('[a-z -]', line)) #keep only letters, spaces and dashes
			line = line.replace('/',' ')
			line = line.replace('citation needed',' ')
			line = line.replace(' - ',' ')
			line = line.strip()
			while '  ' in line:
				line = line.replace('  ',' ')
			if line!='':
				words = line.split(' ')
				j = 0
				while j<len(words):
					temp = words[j].replace('-','')
					if (len(temp)<(len(words[j])-1)) or ('http' in words[j]) or ('ftp' in words[j]) or ('linkback' in words[j]) or (len(words[j])>30) or (words[j]==''):
						trash = words.pop(j)
						del trash
					else:
						j = j+1
				if len(words)>2:
					pageLinesFinal.append(' '.join(words))
	return pageLinesFinal


#define some functions (borrowed from holoword.py)

def normalize(a):
	'''
	Normalize a vector to length 1.
	'''
	return a / numpy.sum(a**2.0)**0.5


def cconv(a, b):
	'''
	Computes the circular convolution of the (real-valued) vectors a and b.
	'''
	return numpy.fft.ifft(numpy.fft.fft(a) * numpy.fft.fft(b)).real


def ordConv(a, b, p1, p2):
	'''
	Performs ordered (non-commutative) circular convolution on the vectors a and
	b by first permuting them according to the index vectors p1 and p2.
	'''
	return cconv(a[p1], b[p2])


def seqOrdConv(l , p1, p2 ):
	'''
	Given a list of vectors, iteratively convolves them into a single vector
	(i.e., "binds" them together: (((1+2)+3)+4)+5 ). Used to combine characters in ngrams.
	'''
	return reduce(lambda a,b: normalize(ordConv(a, b, p1, p2)), l)


#modified from holoword.py
def getOpenNGrams(word, charVecList, charPlaceholder):
	ngrams = []
	sizes = range(len(word))[2:len(word)]
	sizes.append(len(word))
	for size in sizes:
		for i in xrange(len(word)):
			if i+size > len(word): break
			tmp = []
			for char in word[i:(i+size)]:
				tmp.append(charVecList[char])
			ngrams.append(tmp)
			if i+size == len(word): continue
			for b in xrange(1, size):
				for e in xrange(1, len(word)-i-size+1):
					tmp = []
					for char in word[i:(i+b)]:
						tmp.append(charVecList[char])
					tmp.append(charPlaceholder)
					for char in word[(i+b+e):(i+e+size)]:
						tmp.append(charVecList[char])
					ngrams.append(tmp)
	return ngrams


#initialize the character, placeholder and permutation vectors
numpy.random.seed(112358) #set the numpy random seed for (some) replicability
chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '-']
charVecList = {}
for char in chars:
	charVecList[char] = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
charPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
wordPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
perm1 = numpy.random.permutation(vectorLength)
perm2 = numpy.random.permutation(vectorLength)


#initialize an object that can open urls
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

queueToLearner = multiprocessing.Queue()
queueFromLearner = multiprocessing.Queue()


def learnerLoop(coreNum,queueToLearner,queueFromLearner):
	def signalHandler(signal, frame):
		pass
	
	signal.signal(signal.SIGINT, signalHandler)
	os.mkdir('wikiBEAGLEdata/'+str(coreNum))
	wordList = {}
	while True:
		page = 0
		while page==0:
			try:
				page = opener.open('http://en.wikipedia.org/wiki/Special:Random')
			except:
				pass
			if not page==0:
				pageLines = cleanPage(page)
				if len(pageLines)==0:
					page = 0
		for line in pageLines:
			uniqueWords = {}
			words = line.split(' ')
			for word in words:
				if word not in uniqueWords:
					uniqueWords[word] = 1
				else:
					uniqueWords[word] += 1
			for word in uniqueWords:
				if not word in wordList:
					newSize = len(wordList)+1
					if newSize==1:
						formList = numpy.zeros(shape=(newSize,vectorLength))
						contextList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/context', mode='w+', dtype='float', shape=(newSize,vectorLength))
						orderList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/order', mode='w+', dtype='float', shape=(newSize,vectorLength))						
					else:
						formList.resize((newSize,vectorLength))
						del contextList
						del orderList
						contextList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/context', mode='r+', dtype='float', shape=(newSize,vectorLength))
						orderList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/order', mode='r+', dtype='float', shape=(newSize,vectorLength))
					formList[newSize-1] = normalize(numpy.add.reduce([seqOrdConv(ngram,perm1,perm2) for ngram in getOpenNGrams(word, charVecList, charPlaceholder)]))
					wordList[word] = {}
					wordList[word]['frequency'] = uniqueWords[word]
					wordList[word]['index'] = newSize-1
				else:
					wordList[word]['frequency'] += uniqueWords[word]
			#perform encoding
			for j in range(len(words)):
				word = words[j]
				index = wordList[word]['index']
				#context encoding
				for k in range(len(words)):
					if j!=k:
						addWord = wordList[words[k]]
						contextList[index] = contextList[index] + formList[addWord['index']]/addWord['frequency'] #weighting contribution by inverse frequency
				#order encoding
				for order in [1,2,3,4,5,6,7]: #only encode up to 7-grams
					order = order + 1
					for k in range(order):
						if (j-k)>=0:
							if (j+(order-k))<=len(words):
								wordsTmp = words[(j-k):(j+(order-k))]
								forms = [formList[wordList[wordTmp]['index']] for wordTmp in wordsTmp]
								forms[k] = wordPlaceholder
								orderList[index] = orderList[index] + seqOrdConv(forms,perm1,perm2)
			#done a paragraph
			del(forms) #so that we can resize formList later
			contextList.flush()
			orderList.flush()
			queueFromLearner.put(['paragraphs'])
			queueFromLearner.put(['tokens',len(words)])
			if not queueToLearner.empty():
				try:
					del formList
					del contextList
					del orderList
				except:
					pass
				tmp = open('wikiBEAGLEdata/'+str(coreNum)+'/wordList','wb')
				cPickle.dump(wordList,tmp)
				tmp.close()
				sys.exit()


def startLearners():
	if not os.path.exists('wikiBEAGLEdata'):
		os.mkdir('wikiBEAGLEdata')
		runNum = 0
	else:
		files = os.listdir('wikiBEAGLEdata')
		i = 0
		while i < len(files):
			if (files[i][0]=='.') or (files[i]=='context') or (files[i]=='order') or (files[i]=='wordList'):
				trash = files.pop(i)
				del trash
			else:
				i = i + 1
		if len(files)>0:
			runNum = max(map(int,files))+1
		else:
			runNum = 0
	for i in range(numCores):
		exec('learnerProcess'+str(i)+' = multiprocessing.Process(target=learnerLoop,args=('+str(runNum+i)+',queueToLearner,queueFromLearner,))')
		exec('learnerProcess'+str(i)+'.start()')


def killAndCleanUp():
	global paragraphNum
	global tokenNum
	print '\nKilling learners...'
	queueToLearner.put('die')
	dataList = []
	while len(multiprocessing.active_children())>0:
		if queueFromLearner.empty():
			time.sleep(1)
		else:
			message = queueFromLearner.get()
			if message[0]=='paragraphs':
				paragraphNum += 1
			elif message[0]=='tokens':
				tokenNum = tokenNum + message[1]
	tmp = open('wikiBEAGLEprogress.txt','w')
	tmp.write('\n'.join(map(str,[paragraphNum, tokenNum, int(round(timeTaken))])))
	tmp.close()


def signalHandler(signal, frame):
	killAndCleanUp()
	sys.exit()

signal.signal(signal.SIGINT, signalHandler)

if os.path.exists('wikiBEAGLEprogress.txt'):
	tmp = open('wikiBEAGLEprogress.txt','r')
	paragraphNum, tokenNum, timeTaken = map(int,tmp.readlines())
	tmp.close()
else:
	paragraphNum = 0
	tokenNum = 0
	timeTaken = 0

lastUpdateTime = time.time()
os.system('clear')
timeToPrint = str(datetime.timedelta(seconds=round(timeTaken + (time.time()-lastUpdateTime))))
print 'wikiBEAGLE\n\nParagraphs: '+str(paragraphNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint

startLearners()

while len(multiprocessing.active_children())>0:
	if len(multiprocessing.active_children())<numCores:
		print '\nSomething went awry; cleaning up just in case:'
		killAndCleanUp()
		print '\nRestarting learners...'
		startLearners()
	if queueFromLearner.empty():
		time.sleep(1)
	else:
		message = queueFromLearner.get()
		if message[0]=='paragraphs':
			paragraphNum += 1
		elif message[0]=='tokens':
			tokenNum = tokenNum + message[1]
	if (time.time()-lastUpdateTime)>1:
		timeTaken += (time.time()-lastUpdateTime)
		lastUpdateTime = time.time()
		os.system('clear')
		timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
		freeMem = checkFreeMemory()
		print 'wikiBEAGLE\n\nParagraphs: '+str(paragraphNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint+'  Free Memory: '+str(freeMem)+'%'
		if freeMem<lowMemCleanPoint:
			print '\nMemory low, cleaning up:'
			killAndCleanUp()
			print '\nRestarting learners...'
			startLearners()

