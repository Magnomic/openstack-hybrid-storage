# openstack-hybrid-storage

Authors: Harbin Institue of Technology, Weihai. Distributed and Intelligent Computing Lab

## Introduction

This work is based on Openstack-swift 2.14.0 and includes proxy nodes and storage nodes.
Proxy node: Receive the data access request, look up the mapping table, obtain the data storage mapping, and forward the parsed data request to the storage node.
Storage node: store the merged metadata and content data, obtain the data content according to the request of the agent node, and return it to the proxy node.

## Detailed design

![](https://ecommunity.oss-cn-zhangjiakou.aliyuncs.com/read.jpg)
![](https://ecommunity.oss-cn-zhangjiakou.aliyuncs.com/write.jpg)
