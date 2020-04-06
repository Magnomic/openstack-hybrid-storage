import xxhash
import numpy as np
import threading
import random


def synchronized(func):
    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func

def Singleton(cls):
    instances = {}

    @synchronized
    def get_instance(*args, **kw):
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return get_instance

@Singleton
class HashTable:

    def __init__(self):
        k, threshold, cycle = 10, 0.005, 1000
        self.counter = 0
        self.hashFuncNum = k
        self.seeds = []
        for i in range(k):
            self.seeds.append(random.randint(0, 100))
        print(self.seeds)
        self.hash_table = np.zeros(2**25, dtype=int)
        self.counter = 0
        self.cycle = cycle
        self.threshold = cycle * threshold
        self.hot_access = 0
        self.total_access = 0

    def check_hot(self, filename):
        for i in range(self.hashFuncNum):
            hash_code = xxhash.xxh32_intdigest(filename, self.seeds[i]) // 2**7
            hot_val = self.hash_table[hash_code]
            if hot_val < self.threshold:
                return False
        return True

    def add_access(self, filename):
        self.counter += 1
        hot_flag = True
        for i in range(self.hashFuncNum):
            hash_code = xxhash.xxh32_intdigest(filename, self.seeds[i]) // 2**7
            hot_val = self.hash_table[hash_code]
            if hot_val + 1 < self.threshold:
                hot_flag = False
            self.hash_table[hash_code] = hot_val + 1
        if hot_flag:
            self.hot_access += 1
        self.total_access += 1
        if self.counter % self.cycle == 0:
            self.update()
        return hot_flag

    def update(self):
        self.hash_table >> 1

    def start(self, list):
        count = 0
        for file in list:
            count += 1
            if count % self.cycle == 0:
                print(count)
                self.update()
            self.add_access(str(file))
        print('total_access : %d' % self.total_access)
        print('hot_access : %d' % self.hot_access)

