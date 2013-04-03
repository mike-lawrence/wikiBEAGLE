import numpy
from scipy import spatial
import cPickle
import math

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
contextList = numpy.memmap('wikiBEAGLEdata/context', mode='r', dtype='float')
vectorLength = contextList.size/numWords
contextList.resize((numWords,vectorLength))
orderList = numpy.memmap('wikiBEAGLEdata/order', mode='r', dtype='float')
orderList.resize((numWords,vectorLength))

#create normalized combination
#bothList = contextList/((numpy.sum(contextList**2,axis=1)**0.5)[:,numpy.newaxis]) + orderList/((numpy.sum(orderList**2,axis=1)**0.5)[:,numpy.newaxis])


v = [value for key,value in indexList.items()]
k = [key for key,value in indexList.items()]
vSortIndex = sorted(range(len(v)), key=v.__getitem__)
v.sort()
k = [k[i] for i in vSortIndex]
mismatches = [(i,j) for i,j in zip(v,range(len(v))) if i!=j]
print len(mismatches)
# while len(mismatches)>0:
# 	firstMismatch = mismatches[0][1]
# 	v[firstMismatch:] = [i-1 for i in v[firstMismatch:]]
# 	mismatches = [(i,j) for i,j in zip(v,range(len(v))) if i!=j]
# 
# indexList = {}
# for i in range(len(k)):
# 	indexList[k[i]] = v[i]
# 
# f = open('wikiBEAGLEdata/indexList','w')
# cPickle.dump(indexList,f)
# f.close()		


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
# Encode the probe
########

probeText = "` he took the warm bread out of the _ . '"
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

distance = spatial.distance.cdist(probe,orderList,'cosine')[0]
sortedDistanceIndices = numpy.argsort(distance)#[::-1]
sortedDistance = numpy.sort(distance)#[::-1]
top10resonators = []
for i in range(10):
	top10resonators.append([[key for key,value in indexList.items() if value == sortedDistanceIndices[i]],sortedDistance[i]])

print top10resonators

wordsToCheck = ['oven','stove','bag','package','car','elephant']
for i in range(len(wordsToCheck)):
	wordsToCheck[i] = [wordsToCheck[i],distance[indexList[wordsToCheck[i]]]]

print wordsToCheck


########
# check the semantic relatedness to a specific word
########

distance = spatial.distance.cdist(contextList[indexList['teacher']].reshape((1,vectorLength)),contextList,'cosine')[0]
# f = numpy.array([value for key,value in freqList.items()])
# fmax = numpy.max(f)*1.0
# q = f/fmax#numpy.log2(f/fmax)#/math.log(1.0/fmax,2)
# distance = distance*q
sortedDistanceIndices = numpy.argsort(distance)#[::-1]
sortedDistance = numpy.sort(distance)#[::-1]
top10resonators = []
for i in range(20):
	top10resonators.append([[key for key,value in indexList.items() if value == sortedDistanceIndices[i]],sortedDistance[i]])

print top10resonators


########
# Replicate context PCA
########
itemList = ['astronomy','physics','chemistry','psychology','biology','scientific','mathematics','technology','science','scientists','research','sports','team','teams','football','coach','players','sport','baseball','soccer','tennis','basketball','savings','finance','pay','invested','loaned','borrow','lend','invest','investments','bank','spend','save']

tmp = [contextList[index] for index in [indexList[key] for key in itemList]]
numpy.savetxt('temp.txt',tmp)


##R code:
# library(FactoMineR)
# library(ggplot2)
# a = scan('temp.txt')
# a = matrix(a,ncol=1024,byrow=F)
# wordList = c('astronomy','physics','chemistry','psychology','biology','scientific','mathematics','technology','science','scientists','research','sports','team','teams','football','coach','players','sport','baseball','soccer','tennis','basketball','savings','finance','pay','invested','loaned','borrow','lend','invest','investments','bank','spend','save')
# b = PCA(a,scale=F,graph=F)
# b = as.data.frame(b$ind$coord[,1:2])
# b$word = wordList
# ggplot(
# 	data = b
# 	, mapping = aes(
# 		x = Dim.1
# 		, y = Dim.2
# 		, label = word
# 	)
# )+
# geom_text()+
# labs(
# 	x = 'PC1'
# 	, y = 'PC2'
# )+
# coord_fixed()+
# theme(
# 	legend.key = element_blank()
# 	, legend.background = element_rect(fill='grey50')
# 	, panel.grid.major = element_blank()
# 	, panel.grid.minor = element_blank()
# 	, panel.background = element_rect(fill='grey50')
# )



########
# Replicate order PCA
########

itemList = ['door','window','fence','sidewalk','table','a','an','those','your','the','my','drive','fight','play','run','move','buy','get','make','above','across','beneath','around','toward','under','in','inside']

tmp = [orderList[index] for index in [indexList[key] for key in itemList]]
numpy.savetxt('temp.txt',tmp)

##R code:
# library(ggplot2)
# library(FactoMineR)
# a = scan('temp.txt')
# a = matrix(a,ncol=1024,byrow=F)
# wordList = c('door','window','fence','sidewalk','table','a','an','those','your','the','my','drive','fight','play','run','move','buy','get','make','above','across','beneath','around','toward','under','in','inside')
# b = PCA(a,scale=F,graph=F)#[!(wordList%in%c('the','a','in')),]
# b = as.data.frame(b$ind$coord[,1:2])
# b$word = wordList#[!(wordList%in%c('the','a','in'))]
# ggplot(
# 	data = b
# 	, mapping = aes(
# 		x = Dim.1
# 		, y = Dim.2
# 		, label = word
# 	)
# )+
# geom_text()+
# labs(
# 	x = 'PC1'
# 	, y = 'PC2'
# )+
# coord_fixed()+
# theme(
# 	legend.key = element_blank()
# 	, legend.background = element_rect(fill='grey50')
# 	, panel.grid.major = element_blank()
# 	, panel.grid.minor = element_blank()
# 	, panel.background = element_rect(fill='grey50')
# )
