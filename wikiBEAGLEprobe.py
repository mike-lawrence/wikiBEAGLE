import numpy
from scipy import spatial
import cPickle

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
# Get the stored data
########

f = open('wikiBEAGLEdata/indexList','r')
indexList = cPickle.load(f)
f.close()		
numWords = len(indexList)
contextList = numpy.memmap('wikiBEAGLEdata/context', mode='r+', dtype='float')
vectorLength = contextList.size/numWords
contextList.resize((numWords,vectorLength))
orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r+', dtype='float')
orderList.resize((numWords,vectorLength))

########
# Initialize the character, placeholder and permutation vectors
########
numpy.random.seed(112358) #set the numpy random seed for (some) replicability
chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '-']
charVecList = {}
for char in chars:
	charVecList[char] = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)

charPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
wordPlaceholder = normalize(numpy.random.randn(vectorLength) * vectorLength**-0.5)
perm1 = numpy.random.permutation(vectorLength)
perm2 = numpy.random.permutation(vectorLength)


########
# Encode the probe
########

probeText = 'he took the warm bread out of the _'
words = probeText.split(' ')
formList = {}
i = 0
#create probe words
for wordNum in range(len(words)):
	if words[wordNum] == '_':
		j = i
		formList[words[wordNum]] = wordPlaceholder
	else:
		formList[words[wordNum]] = normalize(numpy.add.reduce([seqOrdConv(ngram,perm1,perm2) for ngram in getOpenNGrams(words[wordNum], charVecList, charPlaceholder)]))
	i = i + 1

#encode probe word order
probe = numpy.zeros(shape=(1,vectorLength))
for order in [1,2,3,4,5,6,7]: #only encode up to 7-grams
	order = order + 1
	for k in range(order):
		if (j-k)>=0:
			if (j+(order-k))<=len(words):
				probe += seqOrdConv([formList[wordTmp] for wordTmp in words[(j-k):(j+(order-k))]],perm1,perm2)

########
# compare probe to memory
########

resonance = spatial.distance.cdist(probe,orderList,'cosine')[0]

sortedResonanceIndices = numpy.argsort(resonance)[::-1]
sortedResonance = numpy.sort(resonance)[::-1]

top10resonators = []
for i in range(10):
	top10resonators.append([[key for key,value in indexList.items() if value == sortedResonanceIndices[i]],sortedResonance[i]])

print top10resonators

wordsToCheck = ['oven','stove','bag','package','car','elephant']
for i in range(len(wordsToCheck)):
	wordsToCheck[i] = [wordsToCheck[i],resonance[indexList[wordsToCheck[i]]]]

print wordsToCheck
