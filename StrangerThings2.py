# coding:utf8
import json
import sys
import os
from mimetypes import inited
from typing import Union
# from pkg_resources import NoDists
try:
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
except Exception as e:
    print(e)

core=None

buss_area2={
      'A':{'AP774': 'LM1194', 'AP896': 'LM1193', 'AP776': 'LM1192', 'AP897': 'LM1191', 'AP777': 'LM1190',
            'AP898': 'LM1189', 'AP778': 'LM1188', 'AP899': 'LM1187', 'AP547': 'LM1186', 'AP1109': 'LM1185',
            'AP546': 'LM1184', 'AP1110': 'LM1183', 'AP543': 'LM1182', 'AP1111': 'LM1181', 'AP542': 'LM1180',
            'AP1112': 'LM1179', 'AP502': 'LM1137', 'AP504': 'LM1138', 'AP499': 'LM1139', 'AP498': 'LM1140'},
      'B':{'AP940': 'LM631', 'AP1350': 'LM631', 'AP1351': 'LM632', 'AP941': 'LM632', 'AP1352': 'LM633',
            'AP942': 'LM633', 'AP1353': 'LM634', 'AP943': 'LM634', 'AP1354': 'LM635', 'AP944': 'LM635'}
}
buss_area={
      'A':['AP774', 'AP896', 'AP776', 'AP897', 'AP777'],
      'B':['AP940', 'AP1350', 'AP1351', 'AP941', 'AP1352',
            'AP942', 'AP1353', 'AP943', 'AP1354', 'AP944'],
      'C':['AP1','AP2'],
      'D':['AP3','AP4']
}

# 测试的部分点位
weihai_binarea={'A': ['AP416', 'AP415', 'AP412', 'AP413'],
                'B': ['AP273', 'AP271', 'AP270', 'AP272', 'AP269'],
                'C': ['AP234', 'AP231', 'AP239', 'AP236', 'AP233', 'AP238', 'AP240', 'AP235', 'AP237', 'AP232'],
                'D': ['AP188', 'AP139', 'AP221', 'AP186', 'AP192', 'AP230', 'AP171']}

weihai_normalarea={'A': {'AP415': 'LM490', 'AP412': 'LM489', 'AP413': 'LM491', 'AP416': 'LM492'},
                   'B': {'AP272': 'LM621', 'AP271': 'LM620', 'AP269': 'LM618', 'AP270': 'LM619', 'AP273': 'LM622'},
                   'C': {'AP233': 'LM796', 'AP232': 'LM795', 'AP239': 'LM783', 'AP240': 'LM782', 'AP236': 'LM780',
                                          'AP238': 'LM779', 'AP231': 'LM794', 'AP237': 'LM781', 'AP234': 'LM797', 'AP235': 'LM798'},
                   'D': {'AP186': 'LM831', 'AP230': 'LM834', 'AP139': 'LM833', 'AP192': 'LM835', 'AP171': 'LM832', 'AP221': 'LM830', 'AP188': 'LM829'}}





class Bins():
    """库位管理"""

    def __init__(self, data=None):
        """
        bindata records the attributes related to the storage location. name is the location name, prebin is the preceding point,
        goodsType is the type of goods stored in the location, lockId is the storage location lock ID number, used to complete
        mutually exclusive usage, autoType is the automatic replenishment type of the storage location, autoClearType is the
        automatic clearing type of the storage location, changeSt is the time when the goods in the location change, and
        autoInterval is the time for automatically changing the goods,shareable indicates whether it is shareable;
        """

        self.bindata = namedtuple('bindata', ['name', 'prebin','goodsType', 'lockId', 'autoAddType', 'autoClearType', 'changeSt',
                                              'autoInterval','shareable'])
        self.binarea = self.init_area(data)  #  format:{"area_name":{bin_list:[],index:0,statistic:{}}}  # index records the traversal position, and statistic records the quantity of each type of goods


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

    def update_area(self, data=None, goodsType=0, autoAddType=-1, autoClearType=-1, autoInterval=-1, ifrandom=False,
                    randomTuple=(0, 1),shareable=False):
        """
        literal meaning
        :param data: {area_name:[bins,...]}
        :param goodsType: 将所有库位初始化为hasGods的值
        :param autoAddType: 自动加货
        :param autoClearType: 自动清货
        :param autoInterval: 自动任务间隔
        :param ifrandom: 库位的hasGoods未指定时是否随机
        :return:
        """
        for name, locs in data.items():
            for loc in locs:
                if ifrandom:
                    self.binarea.setdefault(name, {}).setdefault('bin_list', []).append(
                        self.bindata(loc, random.choice(randomTuple), 0, autoAddType, autoClearType, time.time(),
                                     autoInterval))
                else:
                    self.binarea.setdefault(name, {}).setdefault('bin_list', []).append(
                        self.bindata(loc, goodsType, 0, autoAddType, autoClearType, time.time(),
                                     autoInterval))
            self.binarea.setdefault(name, {}).setdefault('index', 0)
        return True

    def update_bin(self,data):
        """

        :param data:
        :return:
        """
        for name,attr in data.items():
            if self.binarea.get(name):
                for i in range(len(self.binarea[name]['bin_list'])):
                    if attr[4]:
                        self.binarea[name]['bin_list'][i]=self.binarea[name]['bin_list'][i]._replace(goodsType=random.choice(attr[5]),autoAddType=attr[1],autoClearType=attr[2],autoInterval=attr[3])
                    else:
                        self.binarea[name]['bin_list'][i]=self.binarea[name]['bin_list'][i]._replace(
                            goodsType=attr[0], autoAddType=attr[1], autoClearType=attr[2],
                            autoInterval=attr[3])

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
        # 尝试获取所有信号量
        await self.acquire_all(semaphores)
        try:
            # 成功获取所有信号量后执行某些操作
            print("All semaphores acquired!")
            await asyncio.sleep(2)  # 模拟一些操作
        finally:
            await self.release_all(semaphores)

    async def choose_pos(self, area_name, state, lockId) -> tuple:
        """
        根据所传入的areaname找出一个状态为state的库位，并将该库位锁定
        :param area_name: 从哪个库区找
        :param state:  寻找状态为state的库位 0:无货 ,1,2,3,4...
        :param lockId:  找到后的锁定
        :return: 库位名和索引位置
        """
        async with self.semaphores[area_name]:
            offect = self.binarea[area_name]['index']  # 保证雨露均沾的遍历
            area_len = len(self.binarea[area_name]['bin_list'])
            for i in range(area_len):
                if self.binarea[area_name]['bin_list'][(i + offect) % area_len].lockId == 0:
                    bin = self.binarea[area_name]['bin_list'][(i + offect) % area_len]
                    if state == 0:
                        if bin.autoClearType == bin.goodsType and time.time() - bin.changeSt > bin.autoInterval:
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                                self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(goodsType=0,
                                                                                                      lockId=lockId)
                            self.binarea[area_name]['index'] = (i + offect) % area_len
                            return bin.name, (i + offect) % area_len
                    if state:
                        if bin.autoAddType == state and time.time() - bin.changeSt > bin.autoInterval:
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                                self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(goodsType=state,
                                                                                                      lockId=lockId)
                            self.binarea[area_name]['index'] = (i + offect) % area_len
                            return bin.name, (i + offect) % area_len
                    if state == bin.goodsType:
                        self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(lockId=lockId)
                        self.binarea[area_name]['index'] = (i + offect) % area_len
                        return bin.name, (i + offect) % area_len
                continue
            return False, False

    async def choose_all(self,area_list:list=None,lock_id:int=None):
        """
        根据传入的区域序列，锁定所有库区，返回锁定后的点位元组
        :param area_list: [(oid,area,state),(oid,area,state,)]
        :return:
        """
        semaphores = [self.semaphores[area[1]] for area in area_list if len(area)==3]
        all_pos=[]
        oid=area_list[0][0]
        await self.acquire_all(semaphores)
        try:
            print("All semaphores acquired!")
            for ele in area_list:
                lockId, area_name, state,*_ = ele
                if len(ele)==4:
                    all_pos.append((area_name,ele[3], self.binarea[area_name]['bin_list'][ele[3]].name))
                else:
                    offect = self.binarea[area_name]['index']  # 保证雨露均沾的遍历
                    area_len = len(self.binarea[area_name]['bin_list'])
                    for i in range(area_len):
                        if self.binarea[area_name]['bin_list'][(i + offect) % area_len].lockId == 0:
                            bin = self.binarea[area_name]['bin_list'][(i + offect) % area_len]
                            if state == 0:
                                if bin.autoClearType == bin.goodsType and time.time() - bin.changeSt > bin.autoInterval:
                                    self.binarea[area_name]['index'] = (i + offect) % area_len
                                    all_pos.append((area_name,(i + offect) % area_len,bin.name))
                                    break
                            if state:
                                if bin.autoAddType == state and time.time() - bin.changeSt > bin.autoInterval:
                                    self.binarea[area_name]['index'] = (i + offect) % area_len
                                    all_pos.append((area_name, (i + offect) % area_len, bin.name))
                                    break
                            if state == bin.goodsType:
                                self.binarea[area_name]['index'] = (i + offect) % area_len
                                all_pos.append((area_name, (i + offect) % area_len, bin.name))
                                break
                    else:
                       all_pos.append(False)
        except Exception as e:
            print(e)
        finally:
            if False not in all_pos:
                for pos in all_pos:
                    self.binarea[area_name]['bin_list'][pos[1]] = \
                        self.binarea[area_name]['bin_list'][pos[1]]._replace(lockId=oid)
            await self.release_all(semaphores)
            return [pos[2] if isinstance(pos,tuple) else pos for pos in all_pos]

    async def get_sequence_pos_full(self,area_list:list,state:int,oid:str,load_index,unload_index,mode,region):
        """
        返回点位数据列表，如果获取不到所有点位返回空
        :param area_list:
        :param state:
        :param oid:
        :return:
        """
        data=[None,None]
        data[0]=(oid,area_list[load_index],state) if isinstance(area_list[load_index],str) else (oid,area_list[load_index][0],state,area_list[load_index][1])
        data[1]=(oid,area_list[unload_index],0) if isinstance(area_list[unload_index],str) else (oid,area_list[unload_index][0],0,area_list[unload_index][1])

        keypos=await self.choose_all(data)
        if False in keypos:
            return
        index=0
        for a in area_list:
            if index==0:
                yield keypos[0]
            if isinstance(a, str):
                if self.binarea.get(a):
                    # 是库位
                    if index==load_index:
                        if mode==0:
                            yield keypos[0]
                        if mode==1:
                            yield self.predata[keypos[0]],keypos[0]
                        if mode==2:
                            yield self.predata[keypos[0]],keypos[0],self.predata[keypos[0]]
                    elif index==unload_index:
                        if mode==0:
                            yield keypos[1]
                        if mode==1:
                            yield self.predata[keypos[1]],keypos[1]
                        if mode==2:
                            yield self.predata[keypos[1]],keypos[1],self.predata[keypos[1]]
                elif self.normal_area.get(a):
                    if self.if_avilable():
                        yield None
                    else:
                        yield random.choice(self.normal_area.get(a))
            else: # tuple
                if index == load_index:
                    if mode == 0:
                        yield keypos[0]
                    if mode == 1:
                        yield self.predata[keypos[0]],keypos[0]
                    if mode == 2:
                        yield self.predata[keypos[0]],keypos[0],self.predata[keypos[0]]
                elif index == unload_index:
                    await self.just_lock(region[unload_index],a[1],oid)
                    if mode == 0:
                        yield keypos[1]
                    if mode == 1:
                        yield self.predata[keypos[1]], keypos[1]
                    if mode == 2:
                        yield self.predata[keypos[1]], keypos[1], self.predata[keypos[1]]
                else:
                    yield self.binarea[a[0]]['bin_list'][a[1]]
            index+=1

    async def change_state(self, area, index, goodsType):
        """
        修改指定库位状态
        :param area: 区域名
        :param index: 区域中第几个库位
        :param goodsType: 更改后库位状态
        :return:
        """
        async with self.semaphores[area]:
            self.binarea[area]['bin_list'][index] = self.binarea[area]['bin_list'][index]._replace(goodsType=goodsType,
                                                                                                   lockId=0,
                                                                                                   changeSt=time.time())
            # print("change")
            return self.binarea[area]['bin_list'][index].name

    async def just_lock(self, area, index, oid):
        """"""
        async with self.semaphores[area]:
            self.binarea[area]['bin_list'][index] = self.binarea[area]['bin_list'][index]._replace(lockId=oid)
                              return self.binarea[area]['bin_list'][index].name


class Business:
    """业务"""

    def __init__(self, business_id: int, region_area: list[str], bins: Bins, vehicles: list=None, goods_type: int=0,
                 from_index: Union[int, str] = 0, to_index: Union[int, str] = 1, group=None, interval=1, const_output=1,
                 mode=0):
        """
        :param business_id: int 业务id
        :param region_area: 搬运区域
        :param from_index: 取货区域
        :param to_index: 取货区域
        :param bins: 库区对象
        :param vehicles: 这些业务需要由哪车完成， 暂时用于跟踪料箱车信息
        :param vehicle_type: 车体类型
        :param goods_type: 取货的货物类型
        :param group: 指定机器人组
        :param interval: 发单间隔等同于生产环境中机器的生产节拍
        :param const_output: 每次需要发单数量，等同于生产环境中机器每次的产量  # note 避免太多未完成运单累计，增加限制 已下发未完成不能超过const_output
        :param mode: 库位的动作模式 0 直接到库位，1 前置点库位， 2 前置点-库位-前置点
        """
        self.business_id = str(business_id)
        self.region_area = region_area
        self.from_index = from_index if isinstance(from_index, int) else self.region_area.index(from_index)
        self.to_index = to_index if isinstance(to_index, int) else self.region_area.index(to_index)
        self.interval = interval
        self.bins = bins
        self.vehicle_type = vehicle_type
        self.goods_type = goods_type
        self.const_output = const_output
        self.group = group
        self.vehicle_dict = None if vehicles is None else {vehicle: {} for vehicle in vehicles}  # {name:{cid:gid}}
        self.runing = [(0, 0, 0) for i in range(self.const_output)]  # 正在执行的运单  (oid,area,index)
        self.mode = mode
        self.core = CoreUtil()
        self.operationArgs={}
        # self.core = None

    async def perform_task_load_box(self):
        """料箱车取货运单
        """
        while True:
            # 等待库位资源
            to_send = self.const_output - sum((0 for i in self.runing if i[0] == 0))
            for i in range(to_send):
                # 选取 load点 ;oid = 'bus' + 1234 + 'type' + {goods_type} +end +xxxxxxxx
                oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                pos, pos_index = await self.bins.choose_pos(area_name=self.region_area[self.from_index],
                                                            state=self.goods_type, lockId=oid)
                if pos:
                    print(f"Business {self.business_id}:load {pos}")
                    self.core.setShareOrder(oid=oid, loc=pos, operation='load', keytask='load',
                                            goodsType=self.goods_type)
                else:
                    # print(f"Business {self.business_id}:can not find load pos")
                    break
                # 让出控制权
                await asyncio.sleep(0)

            # 等待下一个搬运周期
            await asyncio.sleep(self.interval)

    async def perform_task_unload_box(self):
        """每隔设定的时间间隔执行一次搬运操作"""
        while True:
            # 查询机器人是否有新的完成
            for v, c in self.vehicle_dict.items():
                for container in self.core.get_contaioners_data(v):
                    if container['goods_id'].startswith("bus" + self.business_id):
                        if c.get(container["container_name"]) == container["goods_id"]:
                            # 已经放货，未接单
                            continue
                        else:
                            c[container["container_name"]] = container["goods_id"]
                            oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                            pos, pos_index = await self.bins.choose_pos(area_name=self.region_area[self.to_index], state=0, lockId=oid)
                            if pos:
                                print(f"Business {self.business_id}:unload {pos}")
                                if container['container_name'] == '999':
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                            keyGoodsID=container['goods_id'],
                                                            loc=pos)
                                else:
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                            goodsId=container['goods_id'], loc=pos)
                await asyncio.sleep(0.2)

    async def perform_task_box(self,from_points=None,to_points=None):
        """由设备触发的料箱车取货运单"""
        oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
        if from_points:
            pos=await self.bins.just_lock(self.region_area[self.from_index],from_points,oid)
            self.core.setShareOrder(oid=oid, loc=pos, operation='load', keytask='load',
                                    GoodsType=self.goods_type)
        else:
            while True:
                pos, pos_index = await self.bins.choose_pos(area_name=self.region_area[self.from_index],
                                                            state=self.goods_type, lockId=oid)
                if pos:
                    self.core.setShareOrder(oid=oid, loc=pos, operation='load', keytask='load',
                                            GoodsType=self.goods_type)
                    break
                await asyncio.sleep(1)
        while True:
            # 查询机器人是否有新的完成
            for v, c in self.vehicle_dict.items():
                for container in self.core.get_contaioners_data(v):
                    if container['goods_id']==oid:
                        oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                        if to_points:
                            pos = await self.bins.just_lock(self.to_area[self.to_index], to_points, oid)
                            if container['container_name'] == '999':
                                self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                        keyGoodsID=container['goods_id'],
                                                        loc=pos)
                            else:
                                self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                        goodsId=container['goods_id'], loc=pos)
                        else:
                            while True:
                                pos, pos_index = await self.bins.choose_pos(area_name=self.region_area[self.to_index],
                                                                            state=0, lockId=oid)
                                if pos:
                                    print(f"Business {self.business_id}:unload {pos}")
                                    if container['container_name'] == '999':
                                        self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                                keyGoodsID=container['goods_id'],
                                                                loc=pos)
                                    else:
                                        self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                                goodsId=container['goods_id'], loc=pos)
                                    break
                                await asyncio.sleep(1)
                        break
            await asyncio.sleep(1)


    async def perform_task_normal(self, from_appoints=None, to_appoints=None):
        """
        通过addblock取放货
        :param from_appoints: 指定去哪儿放货， 列表：0库位名，1 index ,index指的是该库位在库区中是第几个
        :param to_appoints: 指定去哪儿取货, 同上
        :return:
        """
        print("test",from_appoints,to_appoints)
        # 指定了区域中具体的取货地点，说明是设备触发的业务，运行次数由传过来的from_appoints的长度决定
        if from_appoints is not None and len(from_appoints) > 0:
            from_index = 0
            if self.from_index is not None:
                from_index = self.from_index
            # 判断库位状态 为 有货 且 货物type为 self.load_type【加一层判断更安全】   并且库位没有被锁定
            print("area",self.region_area[from_index])
            if self.bins.binarea[self.region_area[from_index]]['bin_list'][from_appoints[0]].goodsType == self.goods_type and \
            self.bins.binarea[self.region_area[from_index]]['bin_list'][from_appoints[0]].lockId == 0:
                area_list = copy.deepcopy(self.region_area)
                area_list[from_index] = [self.region_area[self.from_index],from_appoints[0]]
                print("create task")
                asyncio.create_task(self.trace_block(area_list))
            return
        # 指定了区域中具体的放货地点，说明是设备触发的业务，运行次数由传过来的to_appoints的长度决定
        if to_appoints is not None  and len(to_appoints) > 0:
            # 判断库位状态 为 有货 且 货物type为 0【加一层判断更安全】
            to_index = 1
            if self.to_index is not None:
                to_index = self.to_index
            if self.bins.binarea[self.region_area[to_index]]['bin_list'][to_appoints[0]].goodsType == 0 and \
            self.bins.binarea[self.region_area[to_index]]['bin_list'][to_appoints[0]].lockId == 0:
                area_list = copy.deepcopy(self.region_area)
                area_list[to_index] = [self.region_area[self.to_index],to_appoints[0]]
                print("create task")
                asyncio.create_task(self.trace_block(area_list))
            return
        # 非设备触发的业务
        while True:
            to_send = self.const_output - sum((0 for i in self.runing if i[0] == 0))
            for i in range(to_send):
                # 发单去
                asyncio.create_task(self.trace_block(self.region_area))
                # 让出CPU
                await asyncio.sleep(0)
            # 等待下一个搬运周期
            await asyncio.sleep(self.interval)


    async def trace_block(self, area_list=None):
        """

        :param area_list: [area,(area,index)]
        :return:
        """
        loadx,unloadx=self.from_index,self.to_index
        oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
        count=-1
        loadpos=None
        async for pos in self.bins.get_sequence_pos_full(area_list,self.goods_type,oid,self.from_index,self.to_index,self.mode,self.region_area):
            if count ==-1:
                load=pos
                if load is None:
                    return
                oid = self.core.setOrder(oid, keyTask="load",keyRoute=loadpos,group=self.group,complete=False)
                count+=1
                continue
            current_s=await self.core.waitState(oid)
            if current_s==0 or current_s==3:
                if isinstance(pos,str):
                    if count == loadx:
                        self.core.addBlock(oid,oid+f":{count}",location=pos,operation='ForkLoad',operationArgs=self.operationArgs)
                    elif count == unloadx:
                        self.core.addBlock(oid, oid + f":{count}", location=pos, operation='ForkUnload',
                                           operationArgs=self.operationArgs)
                elif isinstance(pos,tuple):
                    if count==loadx:
                        if self.mode==1:
                            self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
                            current_s = await self.core.waitState(oid)
                            if current_s==0:
                                self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkLoad')
                            elif current_s > 1:
                                break
                        if self.mode==2:
                            self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
                            current_s = await self.core.waitState(oid)
                            if current_s == 0:
                                self.core.addBlock(oid, oid + f":{count}", location=pos[1], operation='ForkLoad')
                                current_s = await self.core.waitState(oid)
                                if current_s == 0:
                                    self.core.addBlock(oid, oid + f":{count}", location=pos[2], operation='ForkHeight')
                                else:
                                    break
                            else:
                                break
                    elif count==unloadx:
                        if self.mode==1:
                            self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
                            current_s = await self.core.waitState(oid)
                            if current_s==0:
                                self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkUnoad')
                            elif current_s > 1:
                                break
                        if self.mode==2:
                            self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
                            current_s = await self.core.waitState(oid)
                            if current_s == 0:
                                self.core.addBlock(oid, oid + f":{count}", location=pos[1], operation='ForkUload')
                                current_s = await self.core.waitState(oid)
                                if current_s == 0:
                                    self.core.addBlock(oid, oid + f":{count}", location=pos[2], operation='ForkHeight')
                                else:
                                    break
                            else:
                                break
            else:
                break
            count+=1
        self.core.markComplete(oid)



class EL():
    """
    short for Eleven. like Mr.Fantastic, who have a superpower or something,and is extremely sensitive to evil
    """
    gifted_counter = 0

    def __init__(self, bins,data=None):
        """

        :param vehicles:
        :param bins:
        :param data:
        """
        """
        name: 设备名
        teleportFrom: 加工取货地,列表
        teleportTo: 加工放货地,列表
        originGoods: 加工需要的货
        finalType: 加工后产生的货物
        from_area: 取货地的库位归属的区域
        to_area: 放货地的库位归属的区域
        bus_from: 触发补货业务
        bus_to: 触发清货业务
        workingTime: 加工需要的时间   
        changeSt: 上次使用设备的时间
        state: 设备状态，-1表示设备停用，0表示设备启用中，且设备空闲，1表示设备正在加工货物
        paln: 生产计划
        """
        self.normal_manipulation = namedtuple('ability_data',
                                              ['name', 'teleportFrom', 'teleportTo', 'originType', 'finalType',
                                               'from_area', 'to_area', 'bus_from', 'bus_to', 'workingTime', 'changeSt',
                                               'state','area'])
        self.bins = bins
        self.power = self.init_area(data)  # 设备数据结构
        EL.gifted_counter += 1

    def __del__(self):
        pass

    def init_area(self, data):
        """
        初始化设备
        :param data:
        :return:
        """
        # 初始化，teleport_from 、teleport_to
        positions_from=[]
        positions_to=[]
        if data.get("from_area"):
            # 获取 teleport_from 中每个元素在 库位Bins中 from_area 中的位置
            from_area = data['area'].get(data['from_area'])
            # from_area = weihai_binarea.get(data["from_area"])
            positions_from = [
                from_area.index(element) if element in from_area else -1
                for element in data["teleport_from"]
            ]  # 如果元素不存在，返回 -1
            # # 如果有元素不存在，就抛异常
            if positions_from.__contains__(-1):
                raise ValueError(f"teleport_from有误，在from_area找不到")
        if data.get("to_area"):
            # 获取 teleport_to 中每个元素在  库位Bins中 to_area 中的位置
            to_area = data['area'].get(data["to_area"])
            # to_area = weihai_binarea.get(data["to_area"])
            positions_to = [
                to_area.index(element) if element in to_area else -1
                for element in data["teleport_to"]
            ]  # 如果元素不存在，返回 -1
            # # 如果有元素不存在，就抛异常
            if positions_to.__contains__(-1):
                raise ValueError(f"teleport_to有误，在to_area中找不到")
        # 初始化赋值 - 返回
        return self.normal_manipulation(data.get("name", ""),  # 如果不存在返回空字符串
                                        dict(zip(data.get("teleport_from", []), positions_from)),
                                        dict(zip(data.get("teleport_to", []), positions_to)),
                                        data.get("origin_type", ""),
                                        data.get("final_type", ""),
                                        data.get("from_area", ""),
                                        data.get("to_area", ""),
                                        data.get("bus_from", ""),
                                        data.get("bus_to", ""),
                                        data.get("working_time", ""),
                                        data.get("changeSt", ""),
                                        data.get("state", ""),
                                        data.get("area", ""))

    async def get_through(self):
        """
        设备加工货物
        :return:
        """
        while True:
            # 设备空闲，找货物去加工
            if self.power.state == 0:
                # 有from
                if self.power.from_area:
                    # 标记teleportFrom中库位是否有货
                    teleport_flg = True
                    # 设备加工
                    for key, value in self.power.teleportFrom.items():
                        # 判断库位状态 为 有货 且 货物为originType
                        if self.bins.binarea[self.power.from_area]['bin_list'][value].goodsType == self.power.originType:
                            # 将设备设为正在加工货物
                            self.power = self.power._replace(state=1, changeSt=time.time())
                            # 将库位设为空 - 货物这会在设备上
                            await self.bins.change_state(self.power.from_area,value,0)
                            # 触发业务过来放货
                            if self.power.bus_from :
                                asyncio.create_task(self.power.bus_from.perform_task(to_appoints=[value]))
                            # 库位中存在有货库位
                            teleport_flg = False
                            break
                    if teleport_flg:
                        # 代码能走到这里，说明设备空闲的，但没有找到库位去取货，触发业务过来放货
                        if self.power.bus_from:
                            tasks = []
                            for key, value in self.power.teleportFrom.items():
                                appoints = [value]
                                task = asyncio.create_task(self.power.bus_from.perform_task(to_appoints=appoints))
                                tasks.append(task)
                            # 这里是需要等待至少有一个业务补货完成再继续运功设备
                            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                else:
                    # 没有绑定from,设备开始运作即可
                    # 将设备设为正在加工货物
                    self.power = self.power._replace(state=1, changeSt=time.time())
            # 设备运行中，待加工完成，去放货

            if self.power.state == 1 and (time.time() - self.power.changeSt) >= random.gauss(mu=self.power.workingTime,
                                                                                             sigma=0.1 * self.power.workingTime):
                if self.power.to_area:
                    # 标记teleportTo中库位是否有货
                    teleport_flg = True
                    # 获取放置目标库位
                    for key, value in self.power.teleportTo.items():
                        if self.bins.binarea[self.power.to_area]['bin_list'][value].goodsType == 0:
                            await self.bins.change_state(self.power.to_area,value,self.power.finalType)
                            # 加工结束
                            self.power = self.power._replace(state=0)
                            # 出发业务把货拿走
                            if self.power.bus_to:
                                asyncio.create_task(self.power.bus_to.perform_task(from_appoints=[value]))
                            teleport_flg = False
                            break
                    if teleport_flg:
                        # 代码能走到这里，说明设备没有找到库位去放货，触发业务过来取货
                        if self.power.bus_to:
                            tasks = []
                            for key, value in self.power.teleportTo.items():
                                appoints = [value]
                                task = asyncio.create_task(self.power.bus_to.perform_task(from_appoints=appoints))
                                tasks.append(task)
                            # 这里是需要等待至少有一个业务补货完成再继续运功设备
                            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                else :
                    # 没有to
                    # 直接设置设备加工结束即可
                    # 加工结束
                    self.power = self.power._replace(state=0)
            # 让出CPU
            await asyncio.sleep(0.5)


class Demogorgon():
    """
    Evil stuff can affect the development of events
    """
    pass


class OrderSystem:
    def __init__(self, bins):
        self.businesses = []
        self.bins = bins

    def add_business(self, business):
        self.businesses.append(business)

    def balance(self):
        """todo 均衡
        当所有业务形成一个闭环，任意业务效率降低必将影响整体效率，因此，所有业务同时进行时，应考虑如下情况
        1. 各个业务效率固定不变的情况下，如果某个业务运单完成速率降低，该如何动态的调整资源分配
        2. 各个业务效率变化情况，变化符合正太分布，该如何动态的调整资源分配
        """
        pass

    async def run(self):
        """启动所有业务并并发执行"""
        tasks = []
        for business in self.businesses:
            tasks.append(asyncio.create_task(business.perform_task_load_box()))
            tasks.append(asyncio.create_task(business.perform_task_unload_box()))
        # 等待所有任务完成
        tasks.append(asyncio.create_task(self.bins.release_bins()))
        await asyncio.gather(*tasks)

def batch_creation_equipment(bins,data,teleport_from,teleport_to,ratio):
    """
    批量创建设备对象
    :param data: data：name origin_type final_type from_area to_area bus_from bus_to working_time changeSt state area
    :param teleport_from:
    :param teleport_to:
    :param ratio:
    :return:
    """
    # 创建一个空的列表来存储实例
    entities = []
    # 判断 ratio 是否是 (x, 0) 情况
    if ratio[1] == 0:
        teleport_from_chunks = [teleport_from[i:i + ratio[0]] for i in range(0, len(teleport_from), ratio[0])]
        # 遍历两个列表的 chunk 组合
        for teleport_from_chunk in teleport_from_chunks:
            data['teleport_from'] = teleport_from_chunk
            entities.append(EL(bins=bins, data=data))
    # 判断 ratio 是否是 (0, x) 情况
    elif ratio[0] == 0:
        teleport_to_chunks = [teleport_to[i:i + ratio[1]] for i in range(0, len(teleport_to), ratio[1])]
        # 遍历两个列表的 chunk 组合
        for teleport_to_chunk in teleport_to_chunks:
            data['teleport_to'] = teleport_to_chunk
            entities.append(EL(bins=bins, data=data))
    else:
        # 否则按 ratio 分块
        teleport_from_chunks = [teleport_from[i:i + ratio[0]] for i in range(0, len(teleport_from), ratio[0])]
        teleport_to_chunks = [teleport_to[i:i + ratio[1]] for i in range(0, len(teleport_to), ratio[1])]
        # 遍历两个列表的 chunk 组合
        for teleport_from_chunk, teleport_to_chunk in zip(teleport_from_chunks, teleport_to_chunks):
            data['teleport_from'] = teleport_from_chunk
            data['teleport_to'] = teleport_to_chunk
            entities.append(EL(bins=bins, data=data))

    return entities

# async def main():
#     # 初始化发单系统
#     test_data1 = {'A': buss_area.get("A")}
#     test_data2 = {'B': buss_area.get("B")
#                  }
#     test_data3 = {'C': buss_area.get("C")
#                   }
#     test_data4 = {'D': buss_area.get("D")
#                   }
#     bins = Bins()
#     order_system = OrderSystem(bins=bins)
#     vehicles = [f"AMB-0{i}" for i in range(1, 7)]
#     for i in vehicles:
#         # clear containers
#         requests.post(url=f'{cg.ip}/clearAllContainersGoods', json={"vehicle": i})
#         # 机器人行驶速度 + 模拟充电
#         res = requests.post(cg.ip + '/updateSimRobotState', json={
#             "vehicle_id": i,
#             "rotate_speed": 30,
#             "speed": 1,
#             "battery_percentage": 1,
#             # "charge_speed":0.005,
#             # "enable_battery_consumption":True,
#             # "no_task_battery_consumption": 0.05,
#             # "task_battery_consumption":0.35
#         })
#     # core_utils = CoreUtil()
#     # core_utils.set_operation_time(vehicles,operation='script', t = 18)
#     # core_utils.modifyParamNew(data={
#     #     "RDSDispatcher":{
#     #         "MovableParkInPath":True,
#     #         "AutoMovablePark":True,
#     #         "ParkingRobotMoveOthers":True,
#     #         "AutoPark":True,
#     #         "DelayFinishTime":0
#     #     }
#     # })
#     bins.update_area(test_data1, autoAddType=1, autoClearType=1, ifrandom=True)
#     bins.update_area(test_data2, autoAddType=1, autoClearType=1, ifrandom=True)
#     bins.update_area(test_data3, autoAddType=1, autoClearType=1, ifrandom=True)
#     bins.update_area(test_data4, autoAddType=1, autoClearType=1, ifrandom=True)
#     # 设备绑定的点位A
#     teleport_from = ['AP774', 'AP776']
#     # 设备绑定的点位B
#     teleport_to = ['AP940', 'AP1351']
#     # A
#
#     # 1 到 2，运货
#     # bus_data =
#     business1 = Business(business_id=1,region_area=["C","A"], interval=5, const_output=500,
#                          bins=bins,vehicles=vehicles,goods_type=1)
#     business2 = Business(business_id=1, region_area=["B", "D"], interval=5, const_output=500,
#                          bins=bins, vehicles=vehicles, goods_type=1)
#     data = {
#         "name": '01',
#         "teleport_from": teleport_from,
#         "teleport_to": teleport_to,
#         "origin_type": 1,
#         "final_type": 2,
#         "from_area": 'A',
#         "to_area": "B",
#         "bus_from": business1,
#         "bus_to": business2,
#         "working_time": 18,
#         "changeSt": 0,
#         "state": 0
#     }
#     el = EL(vehicles=vehicles, bins=bins, data=data)
#     await el.get_through()
#     # 创建多个业务，每个业务都有不同的搬运周期
#     # # 1 到 2，运货
#     # business1 = Business(business_id=1, from_regions="area1", to_regions="area2", interval=5, const_output=500,
#     #                      bins=bins,vehicles=vehicles,type=1)
#     # # 2 到 3 运货
#     # business2 = Business(business_id=2, from_regions="area2", to_regions="area3", interval=5, const_output=500,
#     #                      bins=bins,vehicles=vehicles,type=1)
#     # # 3 到 2 运空箱
#     # business3 = Business(business_id=3, from_regions="area3", to_regions="area2", interval=5, const_output=500,
#     #                      bins=bins, vehicles=vehicles,type=2)
#     # # 2 到 1 运空箱
#     # business4 = Business(business_id=4, from_regions="area2", to_regions="area1", interval=5, const_output=500,
#     #                      bins=bins, vehicles=vehicles,type=2)
#     #
#     # # 将所有业务添加到系统中
#     # order_system.add_business(business1)
#     # order_system.add_business(business2)
#     # order_system.add_business(business3)
#     # order_system.add_business(business4)
#     # # 启动发单系统
#     # await order_system.run()


# 威海叉车逻辑测试
# async def main():
#     # 初始化发单系统
#     test_data1 = {'A': weihai_binarea.get("A")}
#     test_data2 = {'B': weihai_binarea.get("B")}
#     test_data3 = {'C': weihai_binarea.get("C")}
#     test_data4 = {'D': weihai_binarea.get("D")}
#     bins = Bins()
#     for i, j in weihai_normalarea.items():
#         bins.predata.update(j)
#
#     order_system = OrderSystem(bins=bins)
#     bins.update_area(test_data1, autoAddType=1, autoClearType=0, ifrandom=True,autoInterval=30)
#     bins.update_area(test_data2, autoAddType=1, autoClearType=0, ifrandom=True,autoInterval=30)
#     bins.update_area(test_data3,goodsType=0, autoAddType=0, autoClearType=0,autoInterval=30)
#     bins.update_area(test_data4, autoAddType=0, autoClearType=2, ifrandom=True,autoInterval=30)
#     # a=await bins.choose_all([('111','A',1),('111','B',1)])
#
#     # async for i in bins.get_sequence_pos(['B',("C",5)],1,'test',0,1,1,['B','C']):
#     #     print(i)
#     # async for i in bins.get_sequence_pos_full(['B',("C",5)],1,'test',0,1,1,['B','C']):
#     #     print(i)
#     # 设备绑定的点位A
#     teleport_from = ['AP238', 'AP236']
#     # 设备绑定的点位B
#     teleport_to = ['AP231', 'AP232']
#     # A
#
#     # 1 到 2，运货
#     # bus_data =
#     business1 = Business(business_id=1,region_area=["B","C"], interval=5,
#                          bins=bins,group="CDD14",goods_type=1)
#     business2 = Business(business_id=2, region_area=["C", "D"], interval=5,
#                          bins=bins, group="CDD14", goods_type=2)
#     # await business1.trace_block(['B',("C",5)])
#     data = {
#         "name": '01',
#         "teleport_from": teleport_from,
#         "teleport_to": teleport_to,
#         "origin_type": 1,
#         "final_type": 2,
#         "from_area": 'C',
#         "to_area": "C",
#         "bus_from": business1,
#         "bus_to": business2,
#         "working_time": 60,
#         "changeSt": 0,
#         "state": 0
#     }
#     el = EL(bins=bins, data=data)
#     tasks = []
#     tasks.append(asyncio.create_task(el.get_through()))
#     # tasks.append(asyncio.create_task(business.perform_task_unload_box()))
#     tasks.append(asyncio.create_task(bins.release_bins()))
#     await asyncio.gather(*tasks)


# # 比亚迪料箱车逻辑测试
# async def main():
#     # 初始化发单系统
#     test_data1 = {'I': biyadi.get("I")}
#     test_data2 = {'J': biyadi.get("J")}
#     test_data3 = {'K': biyadi.get("K")}
#     test_data4 = {'L1': biyadi.get("L1")}
#     test_data5 = {'L2': biyadi.get("L2")}
#     test_data6 = {'M': biyadi.get("M")}
#     test_data7 = {'N': biyadi.get("N")}
#
#     bins = Bins()
#
#     order_system = OrderSystem(bins=bins)
#     bins.update_area(test_data1, autoAddType=1, autoClearType=0, ifrandom=True,autoInterval=100)
#     bins.update_area(test_data2, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=0)
#     bins.update_area(test_data3, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=0)
#     bins.update_area(test_data4, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=0)
#     bins.update_area(test_data5, autoAddType=0, autoClearType=0, ifrandom=True,randomTuple=(0,2),autoInterval=0)
#     bins.update_area(test_data6, goodsType=0,autoAddType=0, autoClearType=2,autoInterval=0)
#
#     vehicles1=[f"container-X-0{i}" for i in range(1,5)]
#     vehicles2=["container-D-03" , "container-D-06"]
#     business1 = Business(business_id=1, region_area=["I", "J"], interval=50, const_output=500,
#                     bins=bins, vehicles=vehicles1, goods_type=1)
#     business2 = Business(business_id=2, region_area=["J", "K"], interval=50, const_output=500,
#                     bins=bins, goods_type=1)
#     business3 = Business(business_id=3, region_area=["K", "L1"], interval=50, const_output=500,
#                     bins=bins, goods_type=1)
#     business4 = Business(business_id=4, region_area=["L2", "M"], interval=5,
#                          bins=bins, goods_type=2)
#     business4 = Business(business_id=5, region_area=["M", "N"], interval=5,
#                          bins=bins, vehicles=vehicles2, goods_type=2)
#     # 设备绑定的点位A
#     data = {
#         "name": '01',
#         "teleport_from": "",
#         "teleport_to": "",
#         "origin_type": 1,
#         "final_type": 2,
#         "from_area": 'L1',
#         "to_area": "L2",
#         "bus_from": business3,
#         "bus_to": business4,
#         "working_time": 60,
#         "changeSt": 0,
#         "state": 0
#     }
#     data['teleport_from'] =["DHQ-01"]
#     data['teleport_to'] =["DHQ-02"]
#     el1 = EL(bins=bins, data=data)
#     data['teleport_from'] =["DHQ-03"]
#     data['teleport_to'] =["DHQ-04"]
#     el2 = EL(bins=bins, data=data)
#     data['teleport_from'] = ["DHQ-05"]
#     data['teleport_to'] = ["DHQ-06"]
#     el3 = EL(bins=bins, data=data)
#     data['teleport_from'] = ["DHQ-03"]
#     data['teleport_to'] = ["DHQ-04"]
#     v_el1= EL(bins=bins, data=data)
#     v_el1= EL(bins=bins, data=data)
#
#     tasks = []
#     tasks.append(asyncio.create_task(el1.get_through()))
#     tasks.append(asyncio.create_task(el2.get_through()))
#     tasks.append(asyncio.create_task(el3.get_through()))
#     tasks.append(asyncio.create_task(business.perform_task_unload_box()))
#     tasks.append(asyncio.create_task(business.perform_task_unload_box()))
#     tasks.append(asyncio.create_task(bins.release_bins()))
#     await asyncio.gather(*tasks)


# 比亚迪料箱车逻辑测试
async def main():
    # 初始化发单系统
    test_data1 = {'I': biyadi.get("I")}
    test_data2 = {'J': biyadi.get("J")}
    test_data3 = {'K': biyadi.get("K")}
    test_data4 = {'L1': biyadi.get("L1")}
    test_data5 = {'L2': biyadi.get("L2")}
    test_data6 = {'M': biyadi.get("M")}
    test_data7 = {'N': biyadi.get("N")}

    bins = Bins()

    order_system = OrderSystem(bins=bins)
    bins.update_area(test_data1, autoAddType=1, autoClearType=0, ifrandom=True,autoInterval=100)
    bins.update_area(test_data2, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=100)
    bins.update_area(test_data3, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=0)
    bins.update_area(test_data4, autoAddType=0, autoClearType=0, ifrandom=True,autoInterval=0)
    bins.update_area(test_data5, autoAddType=0, autoClearType=0, ifrandom=True,randomTuple=(0,2),autoInterval=0)
    bins.update_area(test_data6, goodsType=0,autoAddType=0, autoClearType=2,autoInterval=0)

    vehicles1=[f"container-X-0{i}" for i in range(1,5)]
    vehicles2=["container-D-03" , "container-D-06"]
    business1 = Business(business_id=1, region_area=["I", "J"], interval=50, const_output=5,
                    bins=bins, vehicles=vehicles1, goods_type=1)
    business2 = Business(business_id=2, region_area=["J", "K"], interval=50, const_output=5,
                    bins=bins, goods_type=1)
    business3 = Business(business_id=3, region_area=["K", "L1"], interval=50, const_output=5,
                    bins=bins, goods_type=1)
    business4 = Business(business_id=4, region_area=["L2", "M"], interval=5,
                         bins=bins, goods_type=2)
    business4 = Business(business_id=5, region_area=["M", "N"], interval=5,
                         bins=bins, vehicles=vehicles2, goods_type=2)
    # 设备绑定的点位A
    data = {
        "name": '01',
        "teleport_from": "",
        "teleport_to": "",
        "origin_type": 1,
        "final_type": 2,
        "from_area": 'L1',
        "to_area": "L2",
        "bus_from": 3,
        "bus_to": 4,
        "working_time": 60,
        "changeSt": 0,
        "state": 0,
        "area":biyadi
    }
    data['teleport_from'] =["DHQ-01"]
    data['teleport_to'] =["DHQ-02"]
    el1 = EL(bins=bins, data=data)
    data['teleport_from'] =["DHQ-03"]
    data['teleport_to'] =["DHQ-04"]
    el2 = EL(bins=bins, data=data)
    data['teleport_from'] = ["DHQ-05"]
    data['teleport_to'] = ["DHQ-06"]
    el3 = EL(bins=bins, data=data)
    data['teleport_from'] = biyadi.get("J")
    data['teleport_to'] = biyadi.get("K")
    data['working_time'] = 30
    data['bus_from'] = ''
    data['bus_to']=''
    data['final_type']=1
    v_el1= EL(bins=bins, data=data)
    data['teleport_from'] = biyadi.get("M")
    data['teleport_to'] = biyadi.get("N")
    data['final_type'] = 2
    data['origin_type'] = 2

    v_el2 = EL(bins=bins, data=data)
    tasks = []
    # tasks.append(asyncio.create_task(el1.get_through()))
    # tasks.append(asyncio.create_task(el2.get_through()))
    # tasks.append(asyncio.create_task(el3.get_through()))
    # tasks.append(asyncio.create_task(v_el2.get_through()))
    # tasks.append(asyncio.create_task(v_el1.get_through()))
    tasks.append(asyncio.create_task(business1.perform_task_unload_box()))
    tasks.append(asyncio.create_task(business1.perform_task_load_box()))
    tasks.append(asyncio.create_task(bins.release_bins()))
    await asyncio.gather(*tasks)



if __name__ == "__main__":
    # asyncio.run(main())
    # data={'test1':['4'],'test2':['5','6'],'test3':['1','2']}
    # bins=Bins()
    # bins.update_area(data)
    # data2 = { 'test3': ['7', '8']}
    # bins.update_area(data2,ifrandom=True)
    # print(len(bins.semaphores))
    #
    # core=CoreUtil()
    # core.setOrder(location="LM1460")
    asyncio.run(main(),debug=True)

