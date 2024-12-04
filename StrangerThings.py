# coding:utf8
import json
import sys
import os
from mimetypes import inited
from typing import Union

p = os.path.abspath(__file__)
p = os.path.dirname(p)
p = os.path.dirname(p)
p = os.path.dirname(p)
sys.path.append(p)
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
except Exception as e:
    print(e)


class Bins():
    """库位管理"""

    def __init__(self, data=None):
        # self.bindata = namedtuple('bindata', ['bin', 'prebin', 'hasGoods', 'lockId', 'autoAdd', 'autoClear','timestamp','autoInterval'])
        #                                        库位点 前置点  是否有货  锁定的运单id 自动加货 自动清货 状态改变时间戳 自动加货或者清货的间隔
        self.bindata = namedtuple('bindata', ['name', 'goodsType', 'lockId', 'autoAddType', 'autoClearType', 'changeSt',
                                              'autoInterval'])
        self.binarea = self.init_area(data)  # 库区信息 {"area_name":{bin_list:[],index:0}}  # index 记录遍历位置
        self.core = CoreUtil()
        self.normal_area = {}
        self.predata = {}

    def __del__(self):
        pass

    def init_area(self, data):
        """
        :return: return {} if data is None
        """
        return {}

    def _continues_serach(self, lst):
        """"""
        index = 0
        while True:
            if index >= len(lst):
                index = 0
                yield -1, None
            if not lst[index].lockId:
                index += 1
                continue
            else:
                state, op, oid = self.core.getOrderState(lst[index].lockId)
                if state == 'FINISHED' or 'STOPPED':
                    yield index, op, state, oid  # 找到目标元素，返回当前索引
            index += 1

    def update_area(self, data, goodsType=0, autoAddType=0, autoClearType=0, autoInterval=0, ifrandom=False,
                    randomTuple=(0, 1)):
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
                        self.bindata(loc, random.choice(randomTuple), 0, autoAddType, autoClearType, time.time(),
                                     autoInterval))
            self.binarea.setdefault(name, {}).setdefault('index', 0)
        return True

    @property
    def semaphores(self):
        semaphores = {}
        for a in self.binarea.keys():
            semaphores.setdefault(a, asyncio.Semaphore(1))
        return semaphores

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
                            return bin.bin, (i + offect) % area_len
                    if state == bin.hasGoods:
                        self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(lockId=lockId)
                        self.binarea[area_name]['index'] = (i + offect) % area_len
                        return bin.name, (i + offect) % area_len
                continue
            return False, False

    async def release_bins(self):
        """
        运单完成后释放库位
        :return:
        """
        gener = {}
        for k, v in self.binarea.items():
            gener.setdefault(k, self._continues_serach(v['bin_list']))
        while True:
            flag = False
            for area, gen in gener.items():
                try:
                    i, op, state, oid = next(gen)
                    if i != -1:
                        async with self.semaphores[area]:
                            if state == "STOPPED":
                                self.binarea[area]['bin_list'][i] = self.binarea[area]['bin_list'][i]._replace(lockId=0)
                            else:
                                if op == "load":
                                    self.binarea[area]['bin_list'][i] = self.binarea[area]['bin_list'][i]._replace(
                                        goodsType=0, lockId=0, changeSt=time.time())
                                elif op == "unload":
                                    type = oid.split('type')[1].split('end')[0]
                                    self.binarea[area]['bin_list'][i] = self.binarea[area]['bin_list'][i]._replace(
                                        goodsType=oid, lockId=0,
                                        changeSt=time.time())
                    else:
                        flag = True
                except StopIteration:
                    pass
            if flag:
                await asyncio.sleep(5)  # 未修改时等久一点
            await asyncio.sleep(1)

    async def change_state(self, area, index, goodsType):
        async with self.semaphores[area]:
            self.binarea[area]['bin_list'][index] = self.binarea[area]['bin_list'][index]._replace(goodsType=goodsType,
                                                                                                   lockId=0,
                                                                                                   changeSt=time.time())
            return self.binarea[area]['bin_list'][index].name

    async def just_lock(self, area, index, oid):
        """"""
        async with self.semaphores[area]:
            self.binarea[area]['bin_list'][index] = self.binarea[area]['bin_list'][index]._replace(lockId=oid)
            return self.binarea[area]['bin_list'][index].name


class Business:
    """业务"""

    def __init__(self, business_id: int, region_area: list[str], bins: Bins, vehicles: list, goods_type: int,
                 from_index: Union[int, str] = 0, to_index: Union[int, str] = 1, group=None, interval=1, const_output=1,
                 mode=0):
        """
        :param business_id: 业务id
        :param region_area: 搬运取货区域
        :param from_index: 取货区域
        :param to_index: 取货区域
        :param bins: 库区对象
        :param vehicles: 这些业务需要由哪车完成， 暂时用于跟踪料箱车信息
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
        self.goods_type = goods_type
        self.const_output = const_output
        self.group = group
        self.vehicle_dict = {vehicle: {} for vehicle in vehicles}  # {name:{cid:gid}}
        self.runing = [(0, 0, 0) for i in range(self.const_output)]  # 正在执行的运单  (oid,area,index)
        self.mode = mode
        self.core = CoreUtil()

    async def perform_task_load_box(self, from_points=None):
        """料箱车取货运单"""
        if from_points:
            # 设备发的取货
            oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
            pos = await self.bins.just_lock(*from_points, oid)
            self.core.setShareOrder(oid=oid, loc=pos, operation='load', keytask='load', GoodsType=self.goods_type)
        else:
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
                                                GoodsType=self.goods_type)
                    else:
                        # print(f"Business {self.business_id}:can not find load pos")
                        break
                    # 让出控制权
                    await asyncio.sleep(0)

                # 等待下一个搬运周期
                await asyncio.sleep(self.interval)

    async def perform_task_unload_box(self, form_points=None, to_points=None):
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
                            oid = self.business_id + str(uuid.uuid4())
                            pos, pos_index = await self.bins.choose_pos(area_name=self.to_regions, state=0, lockId=oid)
                            if pos:
                                print(f"Business {self.business_id}:unload {pos}")
                                if container['container_name'] == '999':
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                            keyGoodsID=container['goods_id'],
                                                            loc=pos)
                                else:
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',
                                                            goodsId=container['goods_id'], loc=pos)
            await asyncio.sleep(1)

    async def perform_task(self, from_appoints=None, to_appoints=None):
        """
        取放货一体
        :param from_appoints: 指定去哪儿放货， 列表：0库位名，1index ,index指的是该库位在库区中是第几个
        :param to_appoints: 指定去哪儿取货, 同上
        :return:
        """
        # 指定了区域中具体的取货地点，说明是设备触发的业务，运行次数由传过来的from_appoints的长度决定
        if len(from_appoints) > 0:
            # 判断库位状态 为 有货 且 货物type为 self.goods_type【加一层判断更安全】
            if self.bins.binarea[self.from_regions]['bin_list'][from_appoints[1]].goodsType == self.goods_type:
                pass

            return
        # 指定了区域中具体的放货地点，说明是设备触发的业务，运行次数由传过来的to_appoints的长度决定
        if len(to_appoints):
            # 判断库位状态 为 有货 且 货物type为 0【加一层判断更安全】
            if self.bins.binarea[self.to_regions]['bin_list'][to_appoints[1]].goodsType == 0:
                pass
            return
        # 非设备触发的业务
        while True:
            to_send = self.const_output - sum((0 for i in self.runing if i[0] == 0))
            for i in range(to_send):
                # 生成oid = 'bus' + 1234 + 'type' + 1 + xxxxxxxx
                oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                # 选取库位 - 要连续选两个库位
                # 取货库位
                pos1, pos_index1 = await self.bins.choose_pos(area_name=self.from_regions, state=self.goods_type,
                                                              lockId=oid)
                # 放货库位
                pos2, pos_index2 = await self.bins.choose_pos(area_name=self.to_regions, state=0,
                                                              lockId=oid)
                if pos1 and pos2:
                    print(f"Business {self.business_id}:load {pos1}")
                else:
                    # print(f"Business {self.business_id}:can not find load pos,no goodsType: {self.goods_type}")
                    # 要不要break TODO：
                    break
                # 让出CPU
                await asyncio.sleep(0)
            # 等待下一个搬运周期
            await asyncio.sleep(self.interval)

    async def trace_block(self, area_list=None):
        """"""
        pass


class EL():
    """
    short for Eleven. like Mr.Fantastic, who have a superpower or something,and is extremely sensitive to evil
    """
    gifted_counter = 0

    def __init__(self, vehicles, bins, data=None):
        """

        :param vehicles:
        :param bins:
        :param data:
        """
        """
        name: 设备名
        teleportFrom: 加工取货地,列表
        teleportTo: 加工放货地,列表
        originType: 加工前货物类型
        finalType: 加工后货物类型   
        from_area: 取货地的库位归属的区域
        to_area: 放货地的库位归属的区域
        bus_from: 触发取货业务
        bus_to: 绑定的
        workingTime: 加工需要的时间   
        changeSt: 上次使用设备的时间
        state: 设备状态，-1表示设备停用，0表示设备启用中，且设备空闲，1表示设备正在加工货物
        """
        self.normal_manipulation = namedtuple('ability_data',
                                              ['name', 'teleportFrom', 'teleportTo', 'originType', 'finalType',
                                               'from_area', 'to_area', 'bus_from', 'bus_to', 'workingTime', 'changeSt',
                                               'state'])
        self.vehicle_dict = {vehicle: {} for vehicle in vehicles}
        self.power = self.init_area(data)
        self.bins = bins
        EL.gifted_counter += 1

    def __del__(self):
        pass

    def init_area(self, data):
        """
        初始化
        :param data:
        :return:
        """
        # 初始化，teleport_from 、teleport_to
        # 获取 teleport_from 中每个元素在 库位Bins中 from_area 中的位置
        from_area = buss_area.get(data["from_area"])
        positions_from = [
            from_area.index(element) if element in from_area else -1
            for element in data["teleport_from"]
        ]  # 如果元素不存在，返回 -1
        # 如果有元素不存在，就抛异常
        if positions_from.__contains__(-1):
            raise ValueError(f"teleport_from有误，在from_area找不到")
        # 获取 teleport_to 中每个元素在  库位Bins中 to_area 中的位置
        to_area = buss_area.get(data["to_area"])
        positions_to = [
            to_area.index(element) if element in to_area else -1
            for element in data["teleport_to"]
        ]  # 如果元素不存在，返回 -1
        if positions_to.__contains__(-1):
            raise ValueError(f"teleport_to有误，在to_area中找不到")
        # 初始化赋值 - 返回
        return self.normal_manipulation(data["name"],
                                        dict(zip(data["teleport_from"], positions_from)),
                                        dict(zip(data["teleport_to"], positions_to)),
                                        data["origin_type"],
                                        data["final_type"],
                                        data["from_area"],
                                        data["to_area"],
                                        data["bus_from"],
                                        data["bus_to"],
                                        data["working_time"],
                                        data["changeSt"],
                                        data["state"]
                                        )

    async def get_through(self):
        """
        设备加工货物
        :return:
        """
        while True:
            # 设备空闲，找货物去加工
            if self.power.state == 0:
                # 标记teleportFrom中库位是否有货
                teleport_flg = True
                # 设备加工
                for key, value in self.power.teleportFrom.items():
                    # 判断库位状态 为 有货 且 货物为originType
                    if self.bins.binarea[self.power.from_area]['bin_list'][value].goodsType == self.power.originType:
                        # 将设备设为正在加工货物
                        self.power = self.power._replace(state=1, changeSt=time.time())
                        # 将库位设为空 - 货物这会在设备上 TODO:修改为调用方法
                        self.bins.binarea[self.power.from_area]['bin_list'][value] = \
                            self.bins.binarea[self.power.from_area]['bin_list'][value]._replace(goodsType=0)
                        # 触发业务过来放货
                        self.power.bus_from.perform_task_box(to_appoints=self.power.teleportFrom)
                        # 库位中存在有货库位
                        teleport_flg = False
                        break
                if teleport_flg:
                    # 代码能走到这里，说明设备空闲的，但没有找到库位去取货，触发业务过来放货
                    tasks = []
                    for key, value in self.power.teleportFrom.items():
                        appoints = [key, value]
                        task = asyncio.create_task(self.power.bus_from.perform_task_box(to_appoints=appoints))
                        tasks.append(task)
                    # 这里是需要等待至少有一个业务补货完成再继续运功设备
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # 设备运行中，待加工完成，去放货
            if self.power.state == 1 and (time.time() - self.power.changeSt) >= random.gauss(mu=self.power.workingTime,
                                                                                             sigma=0.1 * self.power.workingTime):
                # 标记teleportTo中库位是否有货
                teleport_flg = True
                # 获取放置目标库位
                for key, value in self.power.teleportTo.items():
                    if self.bins.binarea[self.power.to_area]['bin_list'][value].goodsType == 0:
                        # TODO:修改为调用方法
                        self.bins.binarea[self.power.to_area]['bin_list'][value] = \
                            self.bins.binarea[self.power.to_area]['bin_list'][value]._replace(
                                goodsType=self.power.finalType)
                        # 加工结束
                        self.power = self.power._replace(state=0)
                        # 出发业务把货拿走
                        self.power.bus_to.perform_task_box(from_appoints=self.power.teleportTo)
                        teleport_flg = False
                        break
                if teleport_flg:
                    # 代码能走到这里，说明设备没有找到库位去放货，触发业务过来取货
                    tasks = []
                    for key, value in self.power.teleportTo.items():
                        appoints = [key, value]
                        task = asyncio.create_task(self.power.bus_from.perform_task_box(from_appoints=appoints))
                        tasks.append(task)
                    # 这里是需要等待至少有一个业务补货完成再继续运功设备
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
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


async def main():
    # 初始化发单系统
    test_data1 = {'A': buss_area.get("A")}
    test_data2 = {'B': buss_area.get("B")
                  }
    bins = Bins()
    core = CoreUtil()
    order_system = OrderSystem(bins=bins)
    vehicles = [f"AMB-0{i}" for i in range(1, 7)]
    for i in vehicles:
        # clear containers
        requests.post(url=f'{cg.ip}/clearAllContainersGoods', json={"vehicle": i})
        # 机器人行驶速度 + 模拟充电
        res = requests.post(cg.ip + '/updateSimRobotState', json={
            "vehicle_id": i,
            "rotate_speed": 30,
            "speed": 1,
            "battery_percentage": 1,
            # "charge_speed":0.005,
            # "enable_battery_consumption":True,
            # "no_task_battery_consumption": 0.05,
            # "task_battery_consumption":0.35
        })
    # core_utils = CoreUtil()
    # core_utils.set_operation_time(vehicles,operation='script', t = 18)
    # core_utils.modifyParamNew(data={
    #     "RDSDispatcher":{
    #         "MovableParkInPath":True,
    #         "AutoMovablePark":True,
    #         "ParkingRobotMoveOthers":True,
    #         "AutoPark":True,
    #         "DelayFinishTime":0
    #     }
    # })
    bins.update_area(test_data1, autoAddType=1, autoClearType=1, ifrandom=True)
    bins.update_area(test_data2, autoAddType=1, autoClearType=1, ifrandom=True)
    # 设备绑定的点位A
    teleportFrom = ['AP774', 'AP776']
    # 设备绑定的点位B
    teleportTo = ['AP940', 'AP1351']
    # A

    # 1 到 2，运货
    business1 = Business(business_id=1, from_regions="A", to_regions="B", interval=5, const_output=500,
                         bins=bins, vehicles=vehicles, load_type=1, core=core)
    data = {
        "name": '01',
        "teleport_from": teleportFrom,
        "teleport_to": teleportTo,
        "origin_type": 1,
        "final_type": 2,
        "from_area": 'A',
        "to_area": "B",
        "bus_from": business1,
        "bus_to": business1,
        "working_time": 18,
        "changeSt": 0,
        "state": 0
    }
    el = EL(vehicles=vehicles, bins=bins, data=data)
    await el.get_through()
    # 创建多个业务，每个业务都有不同的搬运周期
    # # 1 到 2，运货
    # business1 = Business(business_id=1, from_regions="area1", to_regions="area2", interval=5, const_output=500,
    #                      bins=bins,vehicles=vehicles,type=1)
    # # 2 到 3 运货
    # business2 = Business(business_id=2, from_regions="area2", to_regions="area3", interval=5, const_output=500,
    #                      bins=bins,vehicles=vehicles,type=1)
    # # 3 到 2 运空箱
    # business3 = Business(business_id=3, from_regions="area3", to_regions="area2", interval=5, const_output=500,
    #                      bins=bins, vehicles=vehicles,type=2)
    # # 2 到 1 运空箱
    # business4 = Business(business_id=4, from_regions="area2", to_regions="area1", interval=5, const_output=500,
    #                      bins=bins, vehicles=vehicles,type=2)
    #
    # # 将所有业务添加到系统中
    # order_system.add_business(business1)
    # order_system.add_business(business2)
    # order_system.add_business(business3)
    # order_system.add_business(business4)
    # # 启动发单系统
    # await order_system.run()


if __name__ == "__main__":
    # asyncio.run(main())
    # data={'test1':['4'],'test2':['5','6'],'test3':['1','2']}
    # bins=Bins()
    # bins.update_area(data)
    # data2 = { 'test3': ['7', '8']}
    # bins.update_area(data2,ifrandom=True)
    # print(len(bins.semaphores))
    #
    asyncio.run(main())

