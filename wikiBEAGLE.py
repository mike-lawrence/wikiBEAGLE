import sys
try:
	numCores = sys.argv[1]
except:
	numCores = 1

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


def learnerLoop(queueToLearner,queueFromLearner):
	def signalHandler(signal, frame):
		pass
	
	signal.signal(signal.SIGINT, signalHandler)
	
	freqList = {}
	formList = {}
	contextList = {}
	orderList = {}
	while True:
		page = 0
		while page==0:
			try:
				page = opener.open('http://en.wikipedia.org/wiki/Special:Random')
			except:
				pass
			pageLines = cleanPage(page)
			if len(pageLines)==0:
				page = 0
		for line in pageLines:
			uniqueWords = []
			freqListLine = {}
			words = line.split(' ')
			for word in words:
				if word not in uniqueWords:
					uniqueWords.append(word)
					freqListLine[word] = 1
				else:
					freqListLine[word] += 1
			for word in uniqueWords:
				if not word in formList:
					formList[word] = normalize(numpy.add.reduce([seqOrdConv(ngram,perm1,perm2) for ngram in getOpenNGrams(word, charVecList, charPlaceholder)]))
					contextList[word] = numpy.zeros(vectorLength)
					orderList[word] = numpy.zeros(vectorLength)
					freqList[word] = freqListLine[word]
				else:
					freqList[word] = freqList[word] + freqListLine[word]
			#perform encoding
			for j in range(len(words)):
				word = words[j]
				#context encoding
				for k in range(len(words)):
					if j!=k:
						contextList[word] = contextList[word] + formList[words[k]]/freqList[words[k]] #weighting contribution by inverse frequency
				#order encoding
				for order in [1,2,3,4,5,6,7]: #only encode up to 7-grams
					order = order + 1
					for k in range(order):
						if (j-k)>=0:
							if (j+(order-k))<=len(words):
								wordsTmp = words[(j-k):(j+(order-k))]
								forms = [formList[wordTmp] for wordTmp in wordsTmp]
								forms[k] = wordPlaceholder
								orderList[word] = orderList[word] + seqOrdConv(forms,perm1,perm2)
			#done a paragraph
			queueFromLearner.put(['paragraphs'])
			queueFromLearner.put(['words',len(uniqueWords)])
			queueFromLearner.put(['tokens',len(words)])
			if not queueToLearner.empty():
				queueFromLearner.put(['data',[freqList,formList,contextList,orderList]])
				sys.exit()
			
	

def startLearners():
	for i in range(int(numCores)):
		exec('learnerProcess'+str(i)+' = multiprocessing.Process(target=learnerLoop,args=(queueToLearner,queueFromLearner,))')
		exec('learnerProcess'+str(i)+'.start()')


startLearners()

def killAndCleanUp():
	global paragraphNum
	global tokenNum
	global wordNum
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
			elif message[0]=='words':
				wordNum = wordNum + message[1]
			elif message[0]=='data':
				dataList.append(message[1])
	print '\nAggregating data...'
	if os.path.exists('wikiBeagleData.pkl'):
		tmp = open('wikiBeagleData.pkl','rb')
		oldData = cPickle.load(tmp)
		tmp.close()
		freqList = oldData[0]
		formList = oldData[1]
		contextList = oldData[2]
		orderList = oldData[3]
	else:
		freqList = dataList[0][0]
		formList = dataList[0][1]
		contextList = dataList[0][2]
		orderList = dataList[0][3]
		trash = dataList.pop(0)
		del trash
	for i in range(len(dataList)):
		for j in dataList[i][0]:
			if j in freqList:
				freqList[j] = freqList[j] + dataList[i][0][j]
				formList[j] = formList[j] + dataList[i][1][j]
				contextList[j] = contextList[j] + dataList[i][2][j]
				orderList[j] = orderList[j] + dataList[i][3][j]
			else:
				freqList[j] = dataList[i][0][j]
				formList[j] = dataList[i][1][j]
				contextList[j] = dataList[i][2][j]
				orderList[j] = dataList[i][3][j]					
	tmp = open('wikiBeagleData.pkl','wb')
	cPickle.dump([freqList,formList,contextList,orderList],tmp)
	tmp.close()
	tmp = open('wikiBeagleProgress.txt','w')
	tmp.write('\n'.join(map(str,[paragraphNum, wordNum, tokenNum, int(round(timeTaken))])))
	tmp.close()


def signalHandler(signal, frame):
	killAndCleanUp()
	sys.exit()


signal.signal(signal.SIGINT, signalHandler)

if os.path.exists('wikiBeagleProgress.txt'):
	tmp = open('wikiBeagleProgress.txt','r')
	paragraphNum, wordNum, tokenNum, timeTaken = map(int,tmp.readlines())
	tmp.close()
else:
	paragraphNum = 0
	wordNum = 0
	tokenNum = 0
	timeTaken = 0

lastUpdateTime = time.time()
os.system('clear')
timeToPrint = str(datetime.timedelta(seconds=round(timeTaken + (time.time()-lastUpdateTime))))
print 'wikiBEAGLE\n\nParagraphs: '+str(paragraphNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint

while len(multiprocessing.active_children())>0:
	if queueFromLearner.empty():
		time.sleep(1)
	else:
		message = queueFromLearner.get()
		if message[0]=='paragraphs':
			paragraphNum += 1
		elif message[0]=='tokens':
			tokenNum = tokenNum + message[1]
		elif message[0]=='words':
			wordNum = wordNum + message[1]
	if (time.time()-lastUpdateTime)>1:
		timeTaken += (time.time()-lastUpdateTime)
		lastUpdateTime = time.time()
		os.system('clear')
		timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
		print 'wikiBEAGLE\n\nParagraphs: '+str(paragraphNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
		if checkFreeMemory()<lowMemCleanPoint:
			print '\nMemory low, cleaning up:'
			killAndCleanUp()
			print '\nRestarting learners...'
			startLearners()

	
	
	
