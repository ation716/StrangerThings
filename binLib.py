# coding:utf8
import json
import sys
import os
from mimetypes import inited
from typing import Union
# from pkg_resources import NoDists
import asyncio
import random
import time
import requests
import asyncio
import random
import config as cg
from collections import namedtuple, deque
import uuid
from CoreUtils import CoreUtil
import copy
import heapq
import logging
core=None





class Bins():
    """库位管理"""

    def __init__(self, data=None):
        """
        bindata records the attributes related to the storage location. name is the location name, prebin is the preceding point,
        goodsType is the type of goods stored in the location, lockId is the storage location lock ID number, used to complete
        mutually exclusive usage, autoType is the automatic replenishment type of the storage location, autoClearType is the
        automatic clearing type of the storage location, changeSt is the time when the goods in the location change, and
        autoInterval is the time for automatically changing the goods,shareable indicates whether it is shareable;Priority of
        warehouse slot selection
        """

        self.bindata = namedtuple('bindata', ['name', 'prebin','goodsType', 'lockId', 'changeSt',
                                              'shareable','priority'])
        self.binarea = self.init_area(data)  #  format:{"area_name":{bin_list:[],total_bin:-1,satistic:{goods_type:num},otherInfo{autoTime:-1,autoAdd:-1,autoClear:-1,autoInterval:-1}}}
        self.ttheap={}   # a heap which consist of bin from areas in every goodstype


    def __del__(self):
        """ nothing really matter"""
        pass

    @property
    def semaphores(self):
        """"""
        semaphores = {}
        for a in self.binarea.keys():
            semaphores.setdefault(a, asyncio.Semaphore(1))
        return semaphores

    def init_area(self, data=None):
        """
        :return: return {} if data is None
        """
        self.binarea={}
        if data:
            self.update_area(data)
        return self.binarea

    def update_ttheap(self,area_name,goods_type):
        """
        update self.ttheap[area_name][goods_type]
        :param area_name:
        :param goods_type:
        :return:
        """
        if self.ttheap.get(area_name) is None:
            self.ttheap[area_name] = {}
        self.ttheap[area_name][str(goods_type)]=[]
        for index,ele in enumerate(self.binarea[area_name]['bin_list']):
            pass
            heapq.heappush(self.ttheap[area_name][str(goods_type)],(-ele.priority,ele.changeSt,index))



    def update_area(self, data=None, goodsType:int=0, priority=0,autoAddType=-1, autoClearType=-1, autoInterval=-1, ifrandom=False,
                    randomTuple=(0, 1),shareable=False):
        """
        update binarea data
        :param data: {area_name:[bin_name,...]} or {area_name:{prepoint:point,...}}
        :param goodsType:
        :param autoAddType:
        :param autoClearType:
        :param autoInterval:
        :param ifrandom:
        :param randomTuple:
        :param shareable:
        :return:
        """
        self.acquire_all([_area for _area in self.binarea])
        for area_name, bins in data.items():
            goods_count={}
            bins_count=0
            if isinstance(bins, list):
                for bin_name in bins:
                    if ifrandom: # generate goods randomly
                        gt=random.choice(randomTuple)
                        if goods_count.get(str(gt)):
                            goods_count[str(gt)]+=1
                        else:
                            goods_count[str(gt)]=1
                        self.binarea.setdefault(area_name, {}).setdefault('bin_list', []).append(
                            self.bindata(bin_name, None,str(gt), -1, -1,shareable,priority))
                    else:
                         # generate specified goods
                        if goods_count.get(str(goodsType)):
                            goods_count[str(goodsType)] += 1
                        else:
                            goods_count[str(goodsType)] = 1
                        self.binarea.setdefault(area_name, {}).setdefault('bin_list', []).append(
                            self.bindata(bin_name,None,str(goodsType), -1,-1,shareable,priority))
                    bins_count+=1

            elif isinstance(bins, dict): # has a preceding point, dict format {prePoint:point}
                for bin_name,pre in bins.items():
                    if ifrandom:
                        gt = random.choice(randomTuple)
                        if goods_count.get(str(gt)):  # count goods
                            goods_count[str(gt)] += 1
                        else:
                            goods_count[str(gt)] = 1
                        self.binarea.setdefault(area_name, {}).setdefault('bin_list', []).append(
                            self.bindata(bin_name, pre, str(gt), -1, time.time()+random.randint(1,5), shareable,priority))  # test
                    else:
                        # generate specified goods
                        if goods_count.get(str(goodsType)):
                            goods_count[str(goodsType)] += 1
                        else:
                            goods_count[str(goodsType)] = 1
                        self.binarea.setdefault(area_name, {}).setdefault('bin_list', []).append(
                            self.bindata(bin_name, pre, str(goodsType), -1, -1, shareable,priority))
                    bins_count+=1
            else:
                raise ValueError('bins must be a list or a dict')
            self.binarea.setdefault(area_name, {}).setdefault('total_bin', bins_count)
            self.binarea.setdefault(area_name, {}).setdefault('satistic', goods_count)
            if autoAddType != -1 or autoClearType != -1:
                self.binarea[area_name]['other_info']={}
                self.binarea[area_name]['other_info'].setdefault('autoTime', -1)
                self.binarea[area_name]['other_info'].setdefault('autoAdd', autoAddType)
                self.binarea[area_name]['other_info'].setdefault('autoClear', autoClearType)
                self.binarea[area_name]['other_info'].setdefault('autoInterval', autoInterval)
        return True

    def update_bin(self,area_name,index,goods_type):
        """ for other system update bin data
        """
        with self.semaphores[area_name]:
            self.binarea[area_name]["bin_list"][index]=self.binarea[area_name]["bin_list"][index]._replace(goodsType=goods_type,changeSt=time.time())
            self.push_heap(area_name,goods_type,index)

    def push_heap(self,area_name,goods_type,index):
        """pushed to the heap, then record satistic"""
        bin_t=self.binarea[area_name]['bin_list'][index]
        heapq.heappush(self.ttheap[area_name][str(goods_type)],(bin_t.priority,bin_t.changeSt,index))
        self.binarea[area_name]['satistic'][str(goods_type)]+=1

    def pop_heap(self,area_name,goods_type):
        """opposite of push_heap"""
        self.binarea[area_name]['satistic'][str(goods_type)] -= 1
        print(heapq.heappop(self.ttheap[area_name][str(goods_type)]))
        print(heapq.heappop(self.ttheap[area_name][str(goods_type)]))
        return heapq.heappop(self.ttheap[area_name][str(goods_type)])

    async def acquire_all(self,semaphores:list=None):
        """"""
        tasks = [sem.acquire() for sem in semaphores]
        await asyncio.gather(*tasks)

    async def release_all(self,semaphores:list=None):
        """"""
        for sem in semaphores:
            sem.release()
        print("All semaphores released!")

    async def operate_with_semaphores(self,semaphores:list=None):
        """"""
        await self.acquire_all(semaphores)
        try:
            pass   # something happened
            print("All semaphores acquired!")
            await asyncio.sleep(2)
        finally:
            await self.release_all(semaphores)

    async def choose_pos(self, area_names, goods_type) -> tuple:
        """
        Find a storage location with the status of "goods_type" based on the provided "areaname" and then lock that location.
        :param area_name:
        :param goods_type:
        :return:
        """
        while True:
            if isinstance(area_names,str):
                area_names=[area_names]
            for area_name in area_names:
                _count_goods_type=0 if self.binarea[area_name]['satistic'].get(str(goods_type)) is None else self.binarea[area_name]['satistic'][str(goods_type)]
                if _count_goods_type>0:
                    async with self.semaphores[area_name]:
                        if self.ttheap.get(area_name) is None or self.ttheap[area_name].get(goods_type) is None:
                            self.update_ttheap(area_name,goods_type)
                        return area_name,self.pop_heap(area_name,goods_type)
                else:
                    await asyncio.sleep(2)


    async def choose_all(self, area_name, goods_type, lockId) -> tuple:
        """
        Either you get everything, or you get nothing.
        :param area_name:
        :param goods_type:
        :param lockId:
        :return:
        """
        pass







if __name__ == "__main__":
    buss_area2 = {
        'A': {'AP774': 'LM1194', 'AP896': 'LM1193', 'AP776': 'LM1192', 'AP897': 'LM1191', 'AP777': 'LM1190',
              'AP898': 'LM1189', 'AP778': 'LM1188', 'AP899': 'LM1187', 'AP547': 'LM1186', 'AP1109': 'LM1185',
              'AP546': 'LM1184', 'AP1110': 'LM1183', 'AP543': 'LM1182', 'AP1111': 'LM1181', 'AP542': 'LM1180',
              'AP1112': 'LM1179', 'AP502': 'LM1137', 'AP504': 'LM1138', 'AP499': 'LM1139', 'AP498': 'LM1140'},
        'B': {'AP940': 'LM631', 'AP1350': 'LM631', 'AP1351': 'LM632', 'AP941': 'LM632', 'AP1352': 'LM633',
              'AP942': 'LM633', 'AP1353': 'LM634', 'AP943': 'LM634', 'AP1354': 'LM635', 'AP944': 'LM635'}
    }

    weihai_normalarea = {'A': {'AP415': 'LM490', 'AP412': 'LM489', 'AP413': 'LM491', 'AP416': 'LM492'},
                         'B': {'AP272': 'LM621', 'AP271': 'LM620', 'AP269': 'LM618', 'AP270': 'LM619',
                               'AP273': 'LM622'},
                         'C': {'AP233': 'LM796', 'AP232': 'LM795', 'AP239': 'LM783', 'AP240': 'LM782', 'AP236': 'LM780',
                               'AP238': 'LM779', 'AP231': 'LM794', 'AP237': 'LM781', 'AP234': 'LM797',
                               'AP235': 'LM798'},
                         'D': {'AP186': 'LM831', 'AP230': 'LM834', 'AP139': 'LM833', 'AP192': 'LM835', 'AP171': 'LM832',
                               'AP221': 'LM830', 'AP188': 'LM829'}}
    test=Bins()
    test.update_area(weihai_normalarea,ifrandom=True)
    test.update_ttheap("A",1)
    a=test.choose_pos("A",1)
    a=test.choose_pos("A",1)
    a=test.choose_pos("A",1)

    pass
    time.sleep(2)
    # buss_area = {
    #     'A': ['AP774', 'AP896', 'AP776', 'AP897', 'AP777'],
    #     'B': ['AP940', 'AP1350', 'AP1351', 'AP941', 'AP1352',
    #           'AP942', 'AP1353', 'AP943', 'AP1354', 'AP944'],
    #     'C': ['AP1', 'AP2'],
    #     'D': ['AP3', 'AP4']
    # }
    #
    # # 测试的部分点位
    # weihai_binarea = {'A': ['AP416', 'AP415', 'AP412', 'AP413'],
    #                   'B': ['AP273', 'AP271', 'AP270', 'AP272', 'AP269'],
    #                   'C': ['AP234', 'AP231', 'AP239', 'AP236', 'AP233', 'AP238', 'AP240', 'AP235', 'AP237', 'AP232'],
    #                   'D': ['AP188', 'AP139', 'AP221', 'AP186', 'AP192', 'AP230', 'AP171']}


