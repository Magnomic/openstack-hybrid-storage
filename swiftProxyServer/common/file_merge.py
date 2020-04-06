import threading
import time
import random
import swiftclient.client

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
class fileMerge():

    small_big_map = {}
    big_position = {}
    big_file_name = None
    chunk_list = []
    size_in_chunk = 0
    order_in_chunk = 0
    queue_in_chunk = ''
    queue_in_offset = ''
    chunk_size = 1024*1

    def __init__(self):
        import os
        self.cache_size = 0
        self.small_big_map = {}
        print('generator invoked')
        if os.path.exists('/etc/swift/map_file.data'):
            self.map_fpr = open('/etc/swift/map_file.data', 'r')
            while True:
                line = self.map_fpr.readline()
                if line:
                    try:
                        small_file, big_file = list(line.strip().split('#'))  # fiu : .split(' ')[3: 5])
                        self.small_big_map[small_file] = big_file
                    except ValueError:
                        print('Error with value : %s' % line)
                else:
                    break
            self.map_fpr.close()
            self.map_fpw = open('/etc/swift/map_file.data', 'a')

    @synchronized
    def handle_object(self, small_obj_name, chunk, length, is_message_upload):
        if self.big_file_name is None:
            self.big_file_name = str(time.time()) + str(random.random())
        self.small_big_map[small_obj_name] = self.big_file_name
        self.map_fpw.write('%s#%s\n' % (small_obj_name, self.big_file_name))
        print('%s#%s\n' % (small_obj_name, self.big_file_name))
        self.chunk_list += chunk
        self.queue_in_chunk += '|' + small_obj_name
        self.queue_in_offset += '|' + str(self.size_in_chunk)
        self.size_in_chunk += length
        if is_message_upload is None:
            return [True, None, None, None, None]
        self.queue_in_offset += '|' + str(self.size_in_chunk)
        big_file = self.chunk_list
        big_file_name = self.big_file_name
        queue_in_chunk = self.queue_in_chunk
        queue_in_offset = self.queue_in_offset
        self.big_file_name = None
        self.queue_in_chunk = ''
        self.queue_in_offset = ''
        self.chunk_list = []
        self.size_in_chunk = 0
        return [False, big_file_name, big_file, queue_in_chunk, queue_in_offset]

    def set_small_big_map(self, obj, str_big_file_name):
        self.small_big_map[obj] = str_big_file_name

    def get_small_big_map(self, obj):
        return self.small_big_map[obj]

    def append_chunk(self, chunk):
        self.chunk_list.append(self, chunk)

    def append_chunk_list(self, chunk_list_temp):
        self.chunk_list += chunk_list_temp

    def clear_chunk(self):
        self.chunk_list = []

    def get_chunk(self):
        return self.chunk_list

    def set_order_in_chunk(self, int_value):
        self.order_in_chunk = int_value

    def get_order_in_chunk(self):
        return self.order_in_chunk

    def set_size_in_chunk(self, int_value):
        self.size_in_chunk = int_value

    def get_size_in_chunk(self):
        return self.size_in_chunk

    def set_queue_in_chunk(self, str_value):
        self.queue_in_chunk = str_value

    def get_queue_in_offset(self):
        return self.queue_in_offset

    def set_queue_in_offset(self, str_value):
        self.queue_in_offset = str_value

    def get_queue_in_chunk(self):
        return self.queue_in_chunk

    def set_big_file_name(self, str_value):
        self.big_file_name = str_value

    def get_big_file_name(self):
        return self.big_file_name


    def print_map(self):
        i = 0
        print 'length of map is ' + str(len(self.small_big_map))
        keys = self.small_big_map.keys()
        keys.sort()
        for key in keys:
            i += 1
            print str(i) + 'key : ' + key + 'mapto : ' + self.small_big_map[key]
