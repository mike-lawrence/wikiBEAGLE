#set the length of the vectors (don't change this after you've begun learning)
vectorLength = 2**10

########
# Import all the modules we'll need
########

import sys
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
import tty
import select
import nltk.data
import math


########
# Load the english sentence punkt data
########

tokenizer = nltk.data.load('file:./english.pickle')


########
# Check if multiple cores were requested
########

if len(sys.argv)==1:
	numCores = 1
else:
	numCores = int(sys.argv[1])


########
# Classes to handle quitting safely (from: http://code.activestate.com/recipes/203830/)
########

class NotTTYException(Exception): pass

class TerminalFile:
	def __init__(self,infile):
		if not infile.isatty():
			raise NotTTYException()
		self.file=infile

		#prepare for getch
		self.save_attr=tty.tcgetattr(self.file)
		newattr=self.save_attr[:]
		newattr[3] &= ~tty.ECHO & ~tty.ICANON
		tty.tcsetattr(self.file, tty.TCSANOW, newattr)

	def __del__(self):
		#restoring stdin
		import tty  #required this import here
		tty.tcsetattr(self.file, tty.TCSADRAIN, self.save_attr)

	def getch(self):
		if select.select([self.file],[],[],0)[0]:
			c=self.file.read(1)
		else:
			c=''
		return c


########
# Some text cleaning functions
########

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


#define a function to delete anything inside parens
def removeEncaps(text):
	for encaps in [['(',')'],['[',']']]:
		done = False
		while not done:
			if encaps[0] in text:
				i = 0
				while text[i]!=encaps[0]:
					i += 1
				if encaps[1] in text:
					j = i
					while text[j]!=encaps[1]:
						j += 1
					text = text[0:i]+text[(j+1):]
				else:
					done = True
			else:
				done = True
	return(text)	


#define a function that cleans up a page of text from wikipedia, returning a list of sentences
def cleanPage(page):
	pageLines = page.readlines()
	pageLinesFinal = []
	for thisPageLine in pageLines:
		if thisPageLine[0:3]=='<p>':
			line = delHtml(thisPageLine)
			line = removeEncaps(line)
			line = line.replace('\n','')
			line = line.lower()
			line = line.replace('/',' ')
			line = line.replace('citation needed',' ')
			line = ''.join(re.findall('[a-z 0-9 ,;:.!?-]', line))
			line = line.replace('mr.','mr')
			line = line.replace('mrs.','mrs')
			line = line.replace('ms.','ms')
			line = line.replace('dr.','dr')
			line = line.replace('ex.','ex')
			line = line.replace('e.g.','eg')
			line = line.replace('etc.','etc')
			sentenceList = tokenizer.tokenize(line)
			for line in sentenceList:
				line = line.replace(',',' , ')
				line = line.replace(';',' ; ')
				line = line.replace(':',' : ')
				line = line.replace('.',' . ')
				line = line.replace('!',' ! ')
				line = line.replace('?',' ? ')
				line = line.replace(' - ',' ')
				line = line.replace('-',' - ')
				line = line.strip()
				while '  ' in line:
					line = line.replace('  ',' ')
				if line!='':
					words = line.split(' ')
					j = 0
					while j<len(words):
						if ('http' in words[j]) or ('ftp' in words[j]) or ('linkback' in words[j]) or (len(words[j])>30) or (words[j]==''):
							trash = words.pop(j)
							del trash
						else:
							j = j+1
					if len(words)>2:
						pageLinesFinal.append('` '+' '.join(words))
						if pageLinesFinal[-1][-1]=='.':
							pageLinesFinal[-1] = pageLinesFinal[-1][:-1]+"'"
	return pageLinesFinal


########
# Functions borrowed from holoword.py
########

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


#modified from holoword.py to use the number vectors instead of characters
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


########
# Initialize the character, placeholder and permutation vectors
########

numpy.random.seed(112358) #set the numpy random seed for (some) replicability
chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '`', "'", '-', ',', ';', ':', '.', '!', '?']
charVecList = {}
for char in chars:
	charVecList[char] = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)

charPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
wordPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
perm1 = numpy.random.permutation(vectorLength)
perm2 = numpy.random.permutation(vectorLength)

########
# Initialize an object that can open urls
########

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]


########
# Initialize some multiprocessing queues
########

queueToLearner = multiprocessing.Queue()
queueFromLearner = multiprocessing.Queue()


########
# Initialize the multiprocessing manager (and any old frequency data)
########

manager = multiprocessing.Manager()
if os.path.exists('wikiBEAGLEdata/freqList'):
	tmp = open('wikiBEAGLEdata/freqList')
	freqList = manager.dict(cPickle.load(tmp))
	tmp.close()
else:
	freqList = manager.dict() #to share across learners


########
# Define the loop performed by each learner
########

def learnerLoop(freqList,coreNum,queueToLearner,queueFromLearner):
	os.mkdir('wikiBEAGLEdata/'+str(coreNum))
	indexList = {}
	while True:
		page = 0
		while page==0:
			if not queueToLearner.empty():
				try:
					del formList
					del contextList
					del orderList
				except:
					pass
				tmp = open('wikiBEAGLEdata/'+str(coreNum)+'/indexList','wb')
				cPickle.dump(indexList,tmp)
				tmp.close()				
				queueFromLearner.put('done')
				sys.exit()
			try:
				page = opener.open('http://en.wikipedia.org/wiki/Special:Random')
			except:
				pass
			if not page==0:
				pageLines = cleanPage(page)
				if len(pageLines)==0:
					page = 0
		for line in pageLines:
			if not queueToLearner.empty():
				try:
					del formList
					del contextList
					del orderList
				except:
					pass
				tmp = open('wikiBEAGLEdata/'+str(coreNum)+'/indexList','wb')
				cPickle.dump(indexList,tmp)
				tmp.close()				
				queueFromLearner.put('done')
				sys.exit()
			thisFreqList = {}
			uniqueWords = []
			words = line.split(' ')
			queueFromLearner.put(['tokens',len(words)])
			for word in words:
				if word not in thisFreqList:
					thisFreqList[word] = 1
					uniqueWords.append(word)
				else:
					thisFreqList[word] += 1
			for word in thisFreqList:
				if (not (word in indexList)): #word is new to this learner
					newSize = len(indexList)+1
					if newSize==1: #first new word, initialize lists
						formList = numpy.zeros(shape=(newSize,vectorLength))
						contextList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/context', mode='w+', dtype='float', shape=(newSize,vectorLength))
						orderList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/order', mode='w+', dtype='float', shape=(newSize,vectorLength))						
					else: #resize existinglists
						formList.resize((newSize,vectorLength))
						del contextList
						del orderList
						contextList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/context', mode='r+', dtype='float', shape=(newSize,vectorLength))
						orderList = numpy.memmap('wikiBEAGLEdata/'+str(coreNum)+'/order', mode='r+', dtype='float', shape=(newSize,vectorLength))
					formList[newSize-1] = normalize(numpy.add.reduce([seqOrdConv(ngram,perm1,perm2) for ngram in getOpenNGrams(word, charVecList, charPlaceholder)]))
					indexList[word] = newSize-1
				if word in freqList:
					freqList[word] += thisFreqList[word]
				else:
					freqList[word] = thisFreqList[word]
			#compute sum number of tokens for later scaling of raw word frequencies
			freqs = [v for k,v in freqList.items()]
			maxFreq = max(freqs)*1.0
			#perform context encoding
			for j in range(len(uniqueWords)):
				word = uniqueWords[j]
				index = indexList[word]
				#context encoding
				for k in range(len(uniqueWords)):
					if j!=k:
						contextList[index] = contextList[index] + formList[indexList[uniqueWords[k]]]*(math.log(freqList[uniqueWords[k]]/maxFreq,2)/math.log(1.0/maxFreq,2))#(((2**(-(freqList[uniqueWords[k]]/maxFreq)))-.5)*2) #weighting contribution by inverse frequency
			#perform order encoding
			for j in range(len(words)):
				word = words[j]
				index = indexList[word]
				for order in [1,2,3,4,5,6,7]: #only encode up to 7-grams
					order = order + 1
					for k in range(order):
						if (j-k)>=0:
							if (j+(order-k))<=len(words):
								wordsTmp = words[(j-k):(j+(order-k))]
								forms = [formList[indexList[wordTmp]] for wordTmp in wordsTmp]
								forms[k] = wordPlaceholder
								orderList[index] += seqOrdConv(forms,perm1,perm2)
			#done a sentence
			del(forms) #so that we can resize formList later
			contextList.flush()
			orderList.flush()
			queueFromLearner.put('sentence')
		queueFromLearner.put('page')


########
# Define a function to start the learners
########
def filterFileList(files,filter):
	i = 0
	while i < len(files):
		if files[i][0] in filter:
			trash = files.pop(i)
			del trash
		else:
			i = i + 1
	return files


def startLearners():
	if not os.path.exists('wikiBEAGLEdata'):
		os.mkdir('wikiBEAGLEdata')
		runNum = 0
	else:
		files = os.listdir('wikiBEAGLEdata')
		files = filterFileList(files,['.','c','o','f','p','i'])
		if len(files)>0:
			runNum = max(map(int,files))+1
		else:
			runNum = 0
	for i in range(numCores):
		exec('learnerProcess'+str(i)+' = multiprocessing.Process(target=learnerLoop,args=(freqList,'+str(runNum+i)+',queueToLearner,queueFromLearner,))')
		exec('learnerProcess'+str(i)+'.start()')


########
# Define a function to stop the learners
########

def killAndCleanUp(pageNum, sentenceNum, tokenNum, timeTaken):
	learners_alive = numCores
	wordNum = len(freqList)
	timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
	os.system('clear')
	print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Sentences: '+str(sentenceNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
	print '\nKilling learners... still alive: ' + str(learners_alive)
	lastUpdateTime = time.time()
	queueToLearner.put('die')
	dataList = []
	while learners_alive>0:
		if queueFromLearner.empty():
			time.sleep(1)
		else:
			message = queueFromLearner.get()
			if message=='done':
				learners_alive -= 1
			elif message=='page':
				pageNum += 1
			elif message=='sentence':
				sentenceNum += 1
			elif message[0]=='tokens':
				tokenNum = tokenNum + message[1]
		if (time.time()-lastUpdateTime)>1:
			timeTaken += (time.time()-lastUpdateTime)
			lastUpdateTime = time.time()
			wordNum = len(freqList)
			timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
			os.system('clear')
			print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Sentences: '+str(sentenceNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
			print '\nKilling learners... still alive: ' + str(learners_alive)
	timeTaken += (time.time()-lastUpdateTime)
	wordNum = len(freqList)
	timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
	os.system('clear')
	print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Sentences: '+str(sentenceNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint+'\n\n'
	tmp = open('wikiBEAGLEdata/progress.txt','w')
	tmp.write('\n'.join(map(str,[pageNum, sentenceNum, wordNum, tokenNum, int(round(timeTaken))])))
	tmp.close()
	tmp = open('wikiBEAGLEdata/freqList','wb')
	cPickle.dump(dict(freqList),tmp)
	tmp.close()
	return [pageNum,sentenceNum,tokenNum]


########
# Initialize progress record
########

if os.path.exists('wikiBEAGLEdata/progress.txt'):
	tmp = open('wikiBEAGLEdata/progress.txt','r')
	pageNum, sentenceNum, wordNum, tokenNum, timeTaken = map(int,tmp.readlines())
	tmp.close()
else:
	pageNum = 0
	sentenceNum = 0
	tokenNum = 0
	timeTaken = 0

lastUpdateTime = time.time()
wordNum = len(freqList)
timeToPrint = str(datetime.timedelta(seconds=round(timeTaken + (time.time()-lastUpdateTime))))
os.system('clear')
print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Sentences: '+str(sentenceNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint+'\n\n(Press "q" to quit)'

########
# Go!
########
stdin = TerminalFile(sys.stdin)
startLearners()
while True:
	if stdin.getch()=='q':
		killAndCleanUp(pageNum, sentenceNum, tokenNum, timeTaken)
		sys.exit()
	else:
		if queueFromLearner.empty():
			time.sleep(1)
		else:
			message = queueFromLearner.get()
			if message=='page':
				pageNum += 1
			elif message=='sentence':
				sentenceNum += 1
			elif message[0]=='tokens':
				tokenNum = tokenNum + message[1]
		if (time.time()-lastUpdateTime)>1:
			timeTaken += (time.time()-lastUpdateTime)
			lastUpdateTime = time.time()
			wordNum = len(freqList)
			timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
			os.system('clear')
			print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Sentences: '+str(sentenceNum)+'  Words: '+str(len(freqList))+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint+'\n\n(Press "q" to quit)'

