# coding:utf8
import sys
import os
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
except Exception as e:
    print(e)

class SingletonMetaClass(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMetaClass, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
class CoreUtil(SingletonMetaClass):
    """"""
    def __init__(self,ip:str=""):
        """"""
        self.ip = cg.ip if ip is None else ip

    def getOrderState(self,oid):
        """查询运单状态，返回状态和动作"""
        r = requests.get(self.ip + "/orderDetails/" + oid).json()
        return r.get('state'), r.get('keyTask'),r.get('blocks')[-1]['blockId']

    def setShareOrder(self, **kwargs) -> str:
        """下发标准仿真拼合运单,货物类型暂时支持10种
        :param kwargs:
            loc  load,unload任务位置
            operation load,unload,zero(复位),change(交换背篓)
            changePosition0 change位置1
            changePosition1 change位置2
            goodsId 货物id
            selfPosition 放货位置,注意是背篓位置
            priority 优先级
            goodsType 货物类型
        """
        oid = kwargs.get('oid')
        json_d = {
            'id': oid,
            'keyRoute': kwargs.get('loc'),
            'complete': True,
            'priority': kwargs.get('priority'),
            'vehicle': kwargs.get('vehicle'),
            'keyTask': kwargs.get('operation'),
            'blocks': [
                {
                    'blockId': kwargs.get('goodsType')+oid + ':01',
                    'location': kwargs.get('loc'),
                    "operation": "script",
                    "script_name": "ctuNoBlock.py",
                    "script_args": {
                        "operation": kwargs.get('operation')
                    }
                }
            ]
        }
        if kwargs.get('operation') == 'change':
            json_d['blocks'][0]['script_args']['changePosition0'] = kwargs.get('changePosition0')
            json_d['blocks'][0]['script_args']['changePosition1'] = kwargs.get('changePosition1')
        if kwargs.get('keyGoodsID') is not None:
            json_d['blocks'][0]['keyGoodsId'] = kwargs.get('keyGoodsID')
        else:
            if kwargs.get('operation') == 'load' or kwargs.get('operation') == 'unload':
                json_d['blocks'][0]['goodsId'] = kwargs.get('goodsId') if kwargs.get('goodsId') else oid
                if kwargs.get('selfPosition'):
                    json_d['blocks'][0]['script_args']['selfPosition'] = kwargs.get('selfPosition')
        res = requests.post(url=f"{cg.ip}/setOrder", json=json_d, timeout=10)
        return oid

    def get_contaioners_data(vehicle) -> list:
        r = requests.get(cg.ip + f"/robotsStatus?vehicles={vehicle}").json()
        return r['report'][0]['rbk_report']['containers']


class Bins():
    """库位管理"""
    def __init__(self,data=None):
        # self.bindata = namedtuple('bindata', ['bin', 'prebin', 'hasGoods', 'lockId', 'autoAdd', 'autoClear','timestamp','autoInterval'])
        #                                        库位点 前置点  是否有货  锁定的运单id 自动加货 自动清货 状态改变时间戳 自动加货或者清货的间隔
        self.bindata = namedtuple('bindata', ['name', 'goodsType', 'lockId', 'autoAddType', 'autoClearType','changeSt','autoInterval'])
        self.binarea=self.init_area(data)    # 库区信息 {"area_name":{bin_list:[],index:0}}  # index 记录遍历位置
        self.core=CoreUtil()


    def __del__(self):
        pass

    def init_area(self,data):
        """
        :return: return {} if data is None
        """
        return {}

    def _continues_serach(self,lst):
        """"""
        index = 0
        while True:
            if index >= len(lst):
                index = 0
                yield -1,None
            if not lst[index].lockId:
                index+=1
                continue
            else:
                state,op,block_id=self.core.getOrderState(lst[index].lockId)
                if state=='FINISHED' or 'STOPPED':
                    yield index,op,block_id  # 找到目标元素，返回当前索引
            index += 1

    def update_area(self,data,goodsType=0,autoAddType=0,autoClearType=0,autoInterval=0,ifrandom=False,randomTuple=(0,1)):
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
                    self.binarea.setdefault(name, {}).setdefault('bin_list',[]).append(
                        self.bindata(loc, random.choice(randomTuple), 0, autoAddType, autoClearType, time.time(), autoInterval))
                else:
                    self.binarea.setdefault(name, {}).setdefault('bin_list',[]).append(
                        self.bindata(loc, random.choice(randomTuple), 0, autoAddType, autoClearType, time.time(), autoInterval))
            self.binarea.setdefault(name,{}).setdefault('index',0)
        return True


    @property
    def semaphores(self):
        semaphores={}
        for a in self.binarea.keys():
            semaphores.setdefault(a,asyncio.Semaphore(1))
        return semaphores


    async def choose_pos(self,area_name,state,lockId)->tuple:
        """
        根据所传入的areaname找出一个状态为state的库位，并将该库位锁定
        rule1: 不到autoadd放货，不到autoclear取货
        :param area_name:
        :param state:  寻找状态为state的库位 0:无货 ,1,2,3,4...
        :return: 库位名和索引位置
        """
        async with self.semaphores[area_name]:
            offect=self.binarea[area_name]['index']  # 保证雨露均沾的遍历
            area_len=len(self.binarea[area_name]['bin_list'])
            for i in range(area_len):
                if self.binarea[area_name]['bin_list'][(i+offect)%area_len].lockId==0:
                    bin = self.binarea[area_name]['bin_list'][(i + offect) % area_len]
                    if state==0:
                        if bin.autoClearType==bin.goodsType and time.time()-bin.changeSt>bin.autoInterval:
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(goodsType=0,lockId=lockId)
                            self.binarea[area_name]['index']=(i + offect) % area_len
                            return bin.bin, (i + offect) % area_len
                    if state:
                        if bin.autoAddType==state and time.time()-bin.changeSt>bin.autoInterval:
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                                self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(goodsType=state,lockId=lockId)
                            self.binarea[area_name]['index'] = (i + offect) % area_len
                            return bin.bin, (i + offect) % area_len
                    if state==bin.hasGoods:
                        self.binarea[area_name]['bin_list'][(i + offect) % area_len] = \
                            self.binarea[area_name]['bin_list'][(i + offect) % area_len]._replace(lockId=lockId)
                        self.binarea[area_name]['index'] = (i + offect) % area_len
                        return bin.bin, (i + offect) % area_len
                continue
            return False,False


    async def release_bins(self):
        """
        运单完成后释放库位
        :return:
        """
        gener={}
        for k,v in self.binarea.items():
            gener.setdefault(k,self._continues_serach(v['bin_list']))
        while True:
            flag=False
            for area,gen in gener.items():
                try:
                    i,op,toothless=next(gen)
                    if i!=-1:
                        async with self.semaphores[area]:
                            if op=="load":
                                self.binarea[area]['bin_list'][i]=self.binarea[area]['bin_list'][i]._replace(goodsType=0,lockId=0,changeSt=time.time())
                            elif op=="unload":
                                self.binarea[area]['bin_list'][i] = self.binarea[area]['bin_list'][i]._replace(goodsType=toothless[0], lockId=0,
                                                                                           changeSt=time.time())
                    else:
                        flag=True
                except StopIteration:
                    pass
            if flag:
                await asyncio.sleep(5)
            await asyncio.sleep(1)

class Business:
    """业务"""
    def __init__(self, business_id, from_regions, to_regions, interval, const_output,bins:Bins,vehicles,load_type,region_index=(-1,-1)):
        """

        :param business_id: 业务id
        :param from_regions: 搬运取货区域
        :param to_regions: 搬运放货区域
        :param interval: 发单间隔等同于生产环境中机器的生产节拍
        :param const_output: 每次需要发单数量，等同于生产环境中机器每次的产量  # note 避免太多未完成运单累计，增加限制 已下发未完成不能超过const_output
        :param bins: 库位对象，所有业务共用库位信息
        :param vehicles: 这些业务需要由哪车完成 用于跟踪料箱车信息
        :param region_index: 取放货区域下标
        """
        self.business_id = str(business_id)
        self.from_regions = from_regions
        self.to_regions = to_regions
        self.interval = interval
        self.const_output = const_output
        self.bins = bins
        self.vehicle_dict={vehicle:{} for vehicle in vehicles}  # {name:{cid:gid}}
        self.load_type = load_type
        self.region_index = region_index
        self.runing=[(0,0,0) for i in range(self.const_output)]  # 正在执行的运单  (oid,area,index)
        self.core = CoreUtil()

    async def perform_task_load_box(self):
        """每隔设定的时间间隔执行一次搬运操作"""
        while True:
            # 等待库位资源
            to_send=self.const_output-sum((0 for i in self.runing if i[0]==0))
            for i in range(to_send):
                # 选取 load点 ;oid = 'bus' + 1234 + 'type' + 1 + xxxxxxxx
                oid = "bus" + self.business_id+ "type" + str(self.load_type) + str(uuid.uuid4())
                pos, pos_index = await self.bins.choose_pos(area_name=self.from_regions, state= self.type, lockid=oid)
                if pos:
                    print(f"Business {self.business_id}:load {pos}")
                    self.core.setShareOrder(oid=oid,loc=pos,operation='load',keytask='load',GoodsType=self.load_type)
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
            # print(111111111)
            # 查询机器人是否有新的完成
            for v,c in self.vehicle_dict.items():
                for container in self.core.get_contaioners_data(v):
                    if container['goods_id'].startswith("bus" + self.business_id):
                        if c.get(container["container_name"])==container["goods_id"]:
                            # 已经放货，未接单
                            continue
                        else:
                            c[container["container_name"]] = container["goods_id"]
                            oid = self.business_id + str(uuid.uuid4())
                            pos, pos_index = await self.bins.choose_pos(area_name=self.to_regions, state= 0, lockid=oid)
                            if pos:
                                print(f"Business {self.business_id}:unload {pos}")
                                if container['container_name']=='999':
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload', keyGoodsID=container['goods_id'],
                                                  loc=pos)
                                else:
                                    self.core.setShareOrder(oid=oid,vehicle=v,operation='unload',goodsId=container['goods_id'],loc=pos)
            await asyncio.sleep(1)
class EL():
    """
    short for Eleven. like Mr.Fantastic, who have a superpower or something,and is extremely sensitive to evil
    """
    gifted_counter=0
    def __init__(self, vehicles,bins,data:list=None):
        """"""
        self.normal_manipulation = namedtuple('ability_data',['name','teleportFrom','teleportTo','originType','finalType','from_area','to_area','bus_from','bus_to','chargingTime','changeSt','state'])
        self.vehicle_dict = {vehicle: {} for vehicle in vehicles}
        self.power=self.normal_manipulation(data)
        self.bins = bins
        EL.gifted_counter+=1

    def __del__(self):
        pass

    async def get_through(self):
        """"""
        while True:
            if self.power.state:
                if self.power.changeSt==0:
                    # 开始,只取货
                    pass
                if time.time()-self.power.changeSt>random.gauss(mu=self.power.chargingTime,sigma=0.1*self.power.chargingTime):
                    # 需要取货和放货
                    pass
            await asyncio.sleep(1)




class Demogorgon():
    """
    Evil stuff can affect the development of events
    """
    pass


class OrderSystem:
    def __init__(self,bins):
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
    test_data1={'area1':buss_area.get("busi1")}
    test_data2 = {'area2': buss_area.get("busi2")
                 }
    test_data3 = {'area3': buss_area.get("busi3")}
    bins = Bins()
    order_system = OrderSystem(bins=bins)
    vehicles=[f"AMB-0{i}" for i in range(1,7)]
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
        replay.set_operation_time(i,operation='script', t =18)

    replay.modify_param(data={
        "RDSDispatcher":{
            "MovableParkInPath":True,
            "AutoMovablePark":True,
            "ParkingRobotMoveOthers":True,
            "AutoPark":True,
            "DelayFinishTime":0
        }
    })
    bins.update_area(test_data1, autoAdd=1,autoClear=1,ifrandom=True)
    bins.update_area(test_data2, autoAdd=1, autoClear=1,autoAddX=1, ifrandom=True)
    bins.update_area(test_data3, autoAddX=1,autoClear=1, ifrandom=True)
    # 创建多个业务，每个业务都有不同的搬运周期
    # 1 到 2，运货
    business1 = Business(business_id=1, from_regions="area1", to_regions="area2", interval=5, const_output=500,
                         bins=bins,vehicles=vehicles,type=1)
    # 2 到 3 运货
    business2 = Business(business_id=2, from_regions="area2", to_regions="area3", interval=5, const_output=500,
                         bins=bins,vehicles=vehicles,type=1)
    # 3 到 2 运空箱
    business3 = Business(business_id=3, from_regions="area3", to_regions="area2", interval=5, const_output=500,
                         bins=bins, vehicles=vehicles,type=2)
    # 2 到 1 运空箱
    business4 = Business(business_id=4, from_regions="area2", to_regions="area1", interval=5, const_output=500,
                         bins=bins, vehicles=vehicles,type=2)

    # 将所有业务添加到系统中
    order_system.add_business(business1)
    order_system.add_business(business2)
    order_system.add_business(business3)
    order_system.add_business(business4)
    # 启动发单系统
    await order_system.run()




