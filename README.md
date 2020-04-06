# Openstack-hybrid-storage

Authors: Harbin Institue of Technology, Weihai. Distributed and Intelligent Computing Lab.

Any problem please contact zhudongjie@hit.edu.cn.

## Introduction

This work is based on Openstack-swift 2.14.0 and includes proxy nodes and storage nodes.
Proxy node: Receive the data access request, look up the mapping table, obtain the data storage mapping, and forward the parsed data request to the storage node.
Storage node: store the merged metadata and content data, obtain the data content according to the request of the agent node, and return it to the proxy node.

## Detailed design

### Data merge storage

#### Read process

Flow diagram of the code design
![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/read_process.jpg)

Flow diagram of the architecture design
![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/read.jpg)


#### Write process

Flow diagram of the code design
![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/write_process.jpg)

Flow diagram of the architecture design
![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/write.jpg)
The "stopfile" is a blank file.

### SSD based hybrid storage
We use Bloom Filter based method to define hot-data

![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/hotdata.jpg)

Flow diagram of the replace strategy

![](https://github.com/Magnomic/openstack-hybrid-storage/blob/master/readme_pics/replace_strategy.jpg)

## How to use

Please install Openstack enviorment before deploy our code at (https://docs.openstack.org/swift/latest/getting_started.html).

### On proxy server
>systemctl start openstack-swift-proxy.service memcached.service
>/usr/bin/memcached -d -m 64 -u root -c 1024 -p 11211 -P /tmp/memcached.pid

### On storage server
>systemctl start openstack-swift-account.service openstack-swift-account-auditor.service \
>  openstack-swift-account-reaper.service openstack-swift-account-replicator.service
>systemctl start openstack-swift-container.service \
>  openstack-swift-container-auditor.service openstack-swift-container-replicator.service \
>  openstack-swift-container-updater.service
>systemctl start openstack-swift-object.service openstack-swift-object-auditor.service \
>  openstack-swift-object-replicator.service openstack-swift-object-updater.service

