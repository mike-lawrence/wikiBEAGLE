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
import sys

numpy.seterr('raise')

vectorLength = 2**10

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


def getOpenNGrams(word, charVecList, charPlaceholder):
	# fout = open('tmp.txt','w')
	# fout.write(word+'\n')
	ngrams = []
	sizes = range(len(word))[2:len(word)]
	sizes.append(len(word))
	for size in sizes:
		for i in xrange(len(word)):
			if i+size > len(word): break
			tmp = []
			# fout.write(word[i:(i+size)]+'\n')
			for char in word[i:(i+size)]:
				tmp.append(charVecList[char])
			ngrams.append(tmp)
			if i+size == len(word): continue
			for b in xrange(1, size):
				for e in xrange(1, len(word)-i-size+1):
					tmp = []
					# fout.write(word[i:(i+b)]+'_'+word[(i+b+e):(i+e+size)]+'\n')
					for char in word[i:(i+b)]:
						tmp.append(charVecList[char])
					tmp.append(charPlaceholder)
					for char in word[(i+b+e):(i+e+size)]:
						tmp.append(charVecList[char])
					ngrams.append(tmp)
	# fout.close()
	return ngrams


if not os.path.exists('rands'):
	numpy.random.seed(112358) #set the numpy random seed for (some) replicability
	chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '-']
	charVecList = {}
	for char in chars:
		charVecList[char] = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
	os.mkdir('rands')
	charPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
	wordPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
	perm1 = numpy.random.permutation(vectorLength)
	perm2 = numpy.random.permutation(vectorLength)
	tmp = open('rands/rands','w')
	cPickle.dump([chars,charVecList,charPlaceholder,wordPlaceholder,perm1,perm2],tmp)
	tmp.close()
else:
	tmp = open('rands/rands','r')
	chars,charVecList,charPlaceholder,wordPlaceholder,perm1,perm2 = cPickle.load(tmp)
	tmp.close()	


if not os.path.exists('forms'):
	os.mkdir('forms')

if not os.path.exists('freqs'):
	os.mkdir('freqs')

if not os.path.exists('sems'):
	os.mkdir('sems')
else:
	formList = os.listdir('forms')
	freqList = os.listdir('freqs')
	semList = os.listdir('sems')
	for form in formList:
		if form not in semList:
			os.remove('forms/'+form)
		if form not in freqList:
			os.remove('forms/'+form)
	for freq in freqList:
		if freq not in semList:
			os.remove('freqs/'+freq)
	

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

q_to_learner = multiprocessing.Queue()
q_from_learner = multiprocessing.Queue()

def learner_loop(q_to_learner,q_from_learner):
	def learner_signal_handler(signal, frame):
		pass
	signal.signal(signal.SIGINT, learner_signal_handler)
	formList = os.listdir('forms')
	freqList = os.listdir('freqs')
	semList = os.listdir('sems')
	if os.path.exists('progress.txt'):
		progressFile = open('progress.txt','r')
		progress = progressFile.readlines()
		progressFile.close()
		progress = progress[-1]
		progress = progress.split()
		pageNum = int(progress[0])
		paragraphNum = int(progress[1])
		wordNum = len(semList)
		tokenNum = int(progress[3])
		timeTaken = progress[4]
		if not (':' in timeTaken):
			days = float(timeTaken)
			timeTaken = progress[6]	
		else:
			days = 0	
		timeTaken = timeTaken.split(':')
		hours = float(timeTaken[0])
		minutes = float(timeTaken[1])
		seconds = float(timeTaken[2])
		timeTaken = days*24*60*60 + hours*60*60 + minutes*60 + seconds
	else:
		progressFile = open('progress.txt','w')
		progressFile.write('pageNum paragraphNum wordNum tokenNum timeTaken\n')
		progressFile.close()
		pageNum = 0
		paragraphNum = 0
		wordNum = 0
		tokenNum = 0
		timeTaken = 0
	os.system('clear')
	timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
	print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Paragraphs: '+str(paragraphNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
	done = False
	while not done:
		infile = 0
		try:
			infile = opener.open('http://en.wikipedia.org/wiki/Special:Random')
		except:
			pass
		if infile!=0:
			pageNum += 1
			pageLines = infile.readlines()
			i = -1
			while i < (len(pageLines)-1):
				i += 1
				if pageLines[i][0:3]=='<ti':
					start = 7
					stop = 8
					while pageLines[i][stop:(stop+12)]!=' - Wikipedia':
						stop = stop+1
					title = pageLines[i][start:stop]
					print '\n'+title
				if pageLines[i][0:3]=='<p>':
					line = delHtml(pageLines[i])
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
						paragraphNum += 1
						words = line.split(' ')
						j = 0
						while j<len(words):
							if 'http' in words[j]:
								junk = words.pop(j)
							else:
								j = j+1
						if len(words)>1: #only process if more than one word
							if not q_to_learner.empty():
								done = True
							else:
								#begin processing paragraph
								# fout = open('paragraph.txt','w')
								# fout.write(line)
								# fout.close()
								formList = os.listdir('forms')
								wordNum = len(formList)
								wordFreqList = {}
								formVecList = {}
								semVecList = {}
								uniqueWords = []
								countList = {}
								startTime = time.time()
								os.system('clear')
								timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
								print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Paragraphs: '+str(paragraphNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
								print '\n'+title
								print '\n'+' '.join(words)
								#get the data on each word
								for j in range(len(words)):
									word = words[j]
									if len(word)>255: #truncate to the OS X filename limit
										word = word[0:255]
									if word != '':
										tokenNum += 1
										if word in uniqueWords: #old word (paragraph relative)
											countList[word] += 1
										else: #new word (paragraph relative)
											uniqueWords.append(word)
											countList[word] = 1
											if word in formList: #old word (absolute)
												tmp = open('forms/'+word,'r')
												formVec = cPickle.load(tmp)
												tmp.close()
												tmp = open('sems/'+word,'r')
												semVec = cPickle.load(tmp)
												tmp.close()
												tmp = open('freqs/'+word,'r')
												wordFreq = cPickle.load(tmp) + countList[word]
												tmp.close()
											else: #new word, need to compute form vector
												ngrams = getOpenNGrams(word, charVecList, charPlaceholder)
												formVec = normalize(numpy.add.reduce([seqOrdConv(ngram,perm1,perm2) for ngram in ngrams]))
												wordFreq = countList[word]
												semVec = numpy.zeros(vectorLength)
												tmp = open('forms/'+word,'w')
												cPickle.dump(formVec,tmp)
												tmp.close()
												formList.append(word)
											tmp = open('freqs/'+word,'w')
											cPickle.dump(wordFreq,tmp)
											tmp.close()							
											formVecList[word] = formVec
											wordFreqList[word] = wordFreq
											semVecList[word] = semVec
								#now update the semantic vectors
								for j in range(len(words)):
									word = words[j]
									#context encoding
									contextVec = numpy.zeros(vectorLength)
									for k in range(len(words)):
										if j!=k:
											contextVec = contextVec + formVecList[words[k]]/wordFreqList[words[k]] #weighting contribution by inverse frequency
									contextVec = normalize(contextVec)
									#order encoding
									orderVec = numpy.zeros(vectorLength)
									for order in [1,2,3,4,5,6,7]: #only encode up to 7-grams
										order = order + 1
										for k in range(order):
											if (j-k)>=0:
												if (j+(order-k))<=len(words):
													wordsTmp = words[(j-k):(j+(order-k))]
													forms = [formVecList[wordTmp] for wordTmp in wordsTmp]
													forms[k] = wordPlaceholder
													orderVec = orderVec + seqOrdConv(forms,perm1,perm2)
									#combine superpose context and order info with old vector 
									semVecList[word] = semVecList[word] + normalize(orderVec) + normalize(contextVec)
								#save updated semantic vectors
								for word in uniqueWords:
									tmp = open('sems/'+word,'w')
									cPickle.dump(semVecList[word],tmp)
									tmp.close()
								timeTaken = timeTaken + (time.time()-startTime)
								timeToPrint = str(datetime.timedelta(seconds=round(timeTaken)))
								progressFile = open('progress.txt','a')
								progressFile.write(' '.join(map(str,[pageNum,paragraphNum,wordNum,tokenNum,timeToPrint]))+'\n')
								progressFile.close()
	os.system('clear')
	semList = os.listdir('sems')
	wordNum = len(semList)
	print 'wikiBEAGLE\n\nPages: '+str(pageNum)+'  Paragraphs: '+str(paragraphNum)+'  Words: '+str(wordNum)+'  Tokens: '+str(tokenNum)+'  Time: '+timeToPrint
	progressFile = open('progress.txt','a')
	progressFile.write(' '.join(map(str,[pageNum,paragraphNum,wordNum,tokenNum,timeToPrint]))+'\n')
	progressFile.close()
	q_from_learner.put('done')


learner_process = multiprocessing.Process(target=learner_loop,args=(q_to_learner,q_from_learner,))
learner_process.start()

def signal_handler(signal, frame):
	print 'Quitting...'
	q_to_learner.put('quit')
	while q_from_learner.empty():
		time.sleep(1)
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

while True:
	time.sleep(1)
