import collections

import os

import threading
import time
import socket


exitFlag = 0


class TestCacheThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        test_handle_cache()


def test_handle_cache():
    time.sleep(1)


class CacheThread(threading.Thread):
    def __init__(self, threadID, disk_file_for_big_file, keep_cache):
        threading.Thread.__init__(self)
        self.disk_file_for_big_file = disk_file_for_big_file
        self.threadID = threadID
        self.keep_cache = keep_cache

    def run(self):
        start_time = time.time()
        handle_cache(self.disk_file_for_big_file, self.keep_cache)
        print("use time after %f " % (time.time() - start_time))


def handle_cache(disk_file_for_big_file, keep_cache):
    time.sleep(1)
    with disk_file_for_big_file.open():
        metadata_for_big_file = disk_file_for_big_file.get_metadata()
        name_queue = str(metadata_for_big_file['order_name_queue']).split('|')
        offset_list = str(metadata_for_big_file['offset_queue']).split('|')
        app_iter = disk_file_for_big_file.reader(keep_cache=keep_cache, offset_queue=offset_list)
    cache_helper = fileMerge()
    cache_helper.handle_cache(app_iter, name_queue)


def print_map():
    global small_big_map
    i = 0
    keys = small_big_map.keys()
    keys.sort()
    for key in keys:
        i += 1
        print str(i) + 'key : ' + key + 'mapto : ' + small_big_map[key]


import threading
import time
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

# @Singleton
# class CacheHelper():
#
#     def __init__(self):
#         import socket
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.sock.connect(('localhost', 9011))
#         print('Connected to cache helper')

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
    chunk_size = 1024 * 1024 * 1

    cache_size = 0
    # cache_max_size = 1024*1024*50  # MiB
    cache_max_size = 1024 * 27800000  # KiB

    def __init__(self):
        self.cache_size = 0
        self.cache_show_map = collections.defaultdict(lambda: -1)
        self.cache_map = collections.OrderedDict()
        import memcache
        self.mc = memcache.Client(['127.0.0.1:11211'], debug=True)
        self.mc_meta = memcache.Client(['127.0.0.1:11212'], debug=True)
        # self.logger.write('memcache connected')
        import pika
        credentials = pika.PlainCredentials('openstack', 'seagate_34567')
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            '10.245.150.46', 5672, '/', credentials))
        self.channel = connection.channel()
        # self.logger = open('/var/log/swift-upgrade.log','w')

        self.channel.queue_declare(queue='balance')
        # self.logger.write('channel connected')
        if os.path.exists('/etc/swift/map_file.data'):
            self.map_fpr = open('/etc/swift/map_file.data', 'r')
            while True:
                line = self.map_fpr.readline()
                if line:
                    small_file, big_file = list(line.strip().split('#'))  # fiu : .split(' ')[3: 5])
                    self.small_big_map[small_file] = big_file
                else:
                    break
            self.map_fpr.close()
        if os.path.exists('/etc/swift/position_file.data'):
            self.pos_fpr = open('/etc/swift/position_file.data', 'r')
            while True:
                line = self.pos_fpr.readline()
                if line:
                    file_name, position = line.strip().split('@')
                    self.big_position[file_name] = position.split('$')
                else:
                    break
            self.pos_fpr.close()
        self.pos_fpw = open('/etc/swift/position_file.data', 'a')
        self.map_fpw = open('/etc/swift/map_file.data', 'a')

    def mc_get(self, small_file_name):
        return self.mc.get(small_file_name)

    def mc_get_meta(self, small_file_name):
        return [self.mc_meta.get('%s%s' % (small_file_name, '.meta')), self.mc_meta.get('%s%s' % (small_file_name, '.durable_timestamp'))]

    def mc_set_meta(self, small_file_name, metadata, durable_timestamp):
        self.mc_meta.set('%s%s' % (small_file_name, '.meta'), metadata)
        self.mc_meta.set('%s%s' % (small_file_name, '.durable_timestamp'), durable_timestamp)

    @synchronized
    def handle_object(self, small_obj_name, chunk, length):
        if self.big_file_name is None:
            self.big_file_name = str(time.time()) + str(random.random())
        self.small_big_map[small_obj_name] = self.big_file_name
        self.chunk_list += chunk
        self.queue_in_chunk += '|' + small_obj_name
        self.queue_in_offset += '|' + str(self.size_in_chunk)
        self.size_in_chunk += length
        if self.size_in_chunk < self.chunk_size:
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

    def put_to_cache(self, big_file_name, big_file):
        self.mc.set(big_file_name, big_file)

    @synchronized
    def send_message(self, big_file_name, small_file_path, small_file_name, is_hot):
        # print('prepare for sending')
        # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.connect(('localhost', 9011))
        if not is_hot:
            self.channel.basic_publish(exchange='',
                                  routing_key='balance',
                                  body='%s#%s#%s#%s' % ('dsk', big_file_name, small_file_path, small_file_name))
        else:
            self.channel.basic_publish(exchange='',
                                  routing_key='balance',
                                  body='%s#%s#%s#%s' % ('ssd', big_file_name, small_file_path, small_file_name))
        print('%s#%s#%s#%s' % ('dsk', big_file_name, small_file_path, small_file_name))
        # result = sock.recv(1000000)
        # sock.close()
        # print('closed!')
        return ''

    def handle_cache(self, app_iter, name_queue):
        ite = 1
        result = []
        for file_chunk in app_iter:
            if self.cache_show_map[name_queue[ite]] == 2:  # if this file is deleting, the file cannot be add to cache
                continue
            self.cache_show_map[name_queue[ite]] = 0  # prepared add to cache, cannot read
            try:
                key = self.cache_map[name_queue[ite]]
                del self.cache_map[name_queue[ite]]
            except KeyError:
                self.cache_size += len(file_chunk)
            self.cache_map[name_queue[ite]] = [file_chunk]  # add to cache
            self.cache_show_map[name_queue[ite]] = 1  # finished, cache can be read
            ite += 1
            # print("cache size %d,%d\n" % (len(self.cache_map), self.cache_size))
            if self.cache_max_size < self.cache_size:
                keys_to_del = []
                for key in self.cache_map:
                    try:
                        cache_len = len(''.join(self.cache_map[key]))
                    except KeyError:
                        continue
                    if self.cache_show_map[key] == 0:
                        # if this file is reading to cache, the file cannot be reading, the file will be deleted in
                        # the next deleting process.
                        continue
                    self.cache_show_map[key] = 2
                    self.cache_size -= cache_len
                    keys_to_del.append(key)
                    if self.cache_max_size > self.cache_size:
                        break
                for key in keys_to_del:
                    del self.cache_map[key]
                    self.cache_show_map[key] = -1
        return result

    def get_from_cache(self, small_file_name):
        try:
            return self.cache_map[small_file_name]
        except KeyError:
            return None

    def set_small_big_map(self, obj, str_big_file_name):
        if len(obj) > 0:
            self.map_fpw.write('%s#%s\n' % (obj, str_big_file_name))
        self.small_big_map[obj] = str_big_file_name

    def check_cached(self, small_file_name):
        # for key in self.cache_show_map:
        #     print(key)
        return self.cache_show_map[small_file_name]

    def get_small_big_map(self, obj):
        return self.small_big_map[obj]

    def append_chunk(self, chunk):
        self.chunk_list.append(chunk)

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

    def set_big_position(self, big_file_name, dp_list):
        self.big_position[big_file_name] = dp_list
        self.pos_fpw.write('%s@%s\n' % (big_file_name, '$'.join(dp_list)))
        self.pos_fpw.flush()
        self.map_fpw.flush()

    def get_big_position(self, big_file_name):
        return self.big_position[big_file_name]

    def print_map(self):
        i = 0
        print 'length of map is ' + str(len(self.small_big_map))
        keys = self.small_big_map.keys()
        keys.sort()
        for key in keys:
            i += 1
            print str(i) + 'key : ' + key + 'mapto : ' + self.small_big_map[key]
