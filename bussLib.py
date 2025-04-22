import random
import time

from binLib import Bins
from coreScene import CoreScene
import uuid
from CoreUtils import CoreUtil
import asyncio
import logging

from datetime import datetime



class Business:
    """业务"""

    def __init__(self, business_id: int, bins: Bins=None, from_areas:str="",to_areas:str="",group:str="",label:str="",vehicle_type:str="",goods_type: int=0,
                interval=10, const_output=2,mode=0,recognize:bool=False,vehicles=None):
        """
        :param business_id: int 业务id
        :param bins: 库区对象
        :param from_areas: 取货区域
        :param to_areas: 放货区域
        :param group: 这些业务需要由些组完成， 料箱车需要跟踪料箱车信息
        :param label: 业务需要具有哪些标签的机器人弯成
        :param vehicle_type: 车体类型, 辅助指定动作
        :param goods_type: 取货的货物类型
        :param interval: 发单间隔等同于生产环境中机器的生产节拍
        :param const_output: 每次需要发单数量，等同于生产环境中机器每次的产量  # note 避免太多未完成运单累计，已下发未完成的不能超过const_output, 对于料箱车是保持取货运单数量
        :param mode: 库位的动作模式 0 直接到库位，1 前置点库位， 2 前置点-库位-前置点
        :param recognize: 是否识别
        """
        self.business_id = str(business_id)
        self.bins = bins
        self.from_areas = from_areas
        self.to_areas = to_areas
        self.group = group
        self.label = label if isinstance(label, list) else [label]

        self.vehicle_type = vehicle_type
        self.goods_type = goods_type
        self.interval = interval
        self.const_output = const_output
        self.mode = mode
        self.__vehicles=vehicles
        self.core = CoreUtil()
        self.vehicle2gid = {}.fromkeys(self.vehicles)  # {vehicle:{container:gid}]} 为方便, gid（goods_id）等于 oid
        self.running = [(-1,-1,-1,-1) for i in range(self.const_output)]  # 正在执行的运单  [oid,area,index,0]  最后一位表示状态,0表示取,1表示放
        self._init_container()
        # self.operationArgs={}
        # self.core = None

    async def perform_task_load_box(self):
        """料箱车取货运单
        """
        while True:
            # 计算需要下发的运单
            to_send = self.const_output - sum((1 for i in self.running if i[0]!=-1))
            oids2area=[]
            for i in range(to_send//2):
                # 选取 load点 ;oid = 'bus' + 1234 + 'type' + {goods_type} +end +xxxxxxxx
                oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                area_name, _index = await self.bins.choose_pos(area_names=self.from_areas,goods_type=self.goods_type) # return (bin_t.priority,bin_t.changeSt,index)
                logging.info(f"choose pos {area_name} {self.bins.binarea[area_name]['bin_list'][_index[-1]]}")
                self.core.setShareOrder(oid=oid, loc=self.bins.binarea[area_name]['bin_list'][_index[-1]], operation='load',binTask='load', keytask='load',
                                        goodsType=self.goods_type)
                oids2area.append((oid,area_name,_index[-1],0))
                logging.info(f"{self.business_id} send box load, {oid}")
            else:
                logging.warning(f"Business {self.business_id}:can not find load pos")
                await asyncio.sleep(0.1)
            self._update_running(oids2area)
            self._check_order_finished()
            # 等待下一个搬运周期
            await asyncio.sleep(self.interval)

    def _update_running(self,data):
        """"""
        _i=0
        for i in range(len(self.running)):
            if _i == len(data):
                break
            if self.running[i][0]==-1:
                self.running[i]=data[_i]
                _i+=1


    def _check_order_finished(self):
        """检查 self.running里的运单完成情况"""
        while True:
            for i in range(len(self.running)):
                if self.core.getOrderState(self.running[i][0])=="FINISHED":
                    # 运单完成需要更新库位
                    self.bins.update_bin(i[1],i[2],0 if i[3]==0 else self.goods_type)
                    self.running[i]=(-1,-1,-1,-1)
                    yield True
                else:
                    time.sleep(0.2)
                    continue
            yield False

    def _init_container(self):
        """初始化背篓信息
        rule: 认为self.vehicle中的机器人的背篓数量和编号都是一样的
        """
        containers=self.core.get_contaioners_data(self.vehicles[0])
        containers_id={c['container_name']:-1 for c in containers}
        for v in self.vehicles:
            self.vehicle2gid[v] = containers_id
        logging.info(f"init containers")
    @property
    def vehicles(self):
        """获取场景信息中属于某个机器人组或机器人标签的所有机器人"""
        if self.__vehicles is not None:
            return self.__vehicles
        data=self.core.get_robot_status()
        cs=CoreScene()
        vehicles={}
        for i in data:
            for label in cs.scene['labels']:
                if label['name'] in self.label:
                    for v in label['robotIds']:
                        vehicles.setdefault(v,1)
            for group,vs in cs.robotgroup.items():
                if group == self.group:
                    for v in vs:
                        vehicles.setdefault(v,1)
        self.__vehicles=list(vehicles.keys())
        return self.__vehicles


    async def perform_task_unload_box(self):
        """放货运单"""
        while True:
            # 查询机器人背篓信息
            for v, c in self.vehicle2gid.items():
                for container in self.core.get_contaioners_data(v):
                    if container['goods_id'].startswith("bus" + self.business_id):
                        if c.get(container["container_name"]) == container["goods_id"]:
                            # 已经放货，未接单
                            continue
                        else:
                            c[container["container_name"]] = container["goods_id"]
                            oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
                            area_name, _info = await self.bins.choose_pos(area_names=self.to_areas, goods_type=0)
                            if _info:
                                logging.info(f"Business {self.business_id}:unload {area_name} {_info[-1]}")
                                if container['container_name'] == '999':
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',binTask='unload',
                                                            keyGoodsID=container['goods_id'],
                                                            loc=self.bins.binarea[area_name]['bin_list'][_info[-1]])
                                else:
                                    self.core.setShareOrder(oid=oid, vehicle=v, operation='unload',binTask='unload',
                                                            goodsId=container['goods_id'], loc=self.bins.binarea[area_name]['bin_list'][_info[-1]])
                                self._update_running([(oid,area_name,_info[-1],1)])
                await asyncio.sleep(0.2)


    # async def perform_task_normal(self):
    #     """
    #     通过addblock取放货,
    #     :param from_appoints: 指定去哪儿放货， 列表：0库位名，1 index ,index指的是该库位在库区中是第几个
    #     :param to_appoints: 指定去哪儿取货, 同上
    #     :return:
    #     """
    #     logging.info("test",from_appoints,to_appoints)
    #     # 指定了区域中具体的取货地点，说明是设备触发的业务，运行次数由传过来的from_appoints的长度决定
    #     if from_appoints is not None and len(from_appoints) > 0:
    #         from_index = 0
    #         if self.from_index is not None:
    #             from_index = self.from_index
    #         # 判断库位状态 为 有货 且 货物type为 self.load_type【加一层判断更安全】   并且库位没有被锁定
    #         print("area",self.region_area[from_index])
    #         if self.bins.binarea[self.region_area[from_index]]['bin_list'][from_appoints[0]].goodsType == self.goods_type and \
    #         self.bins.binarea[self.region_area[from_index]]['bin_list'][from_appoints[0]].lockId == 0:
    #             area_list = copy.deepcopy(self.region_area)
    #             area_list[from_index] = [self.region_area[self.from_index],from_appoints[0]]
    #             print("create task")
    #             asyncio.create_task(self.trace_block(area_list))
    #         return
    #     # 指定了区域中具体的放货地点，说明是设备触发的业务，运行次数由传过来的to_appoints的长度决定
    #     if to_appoints is not None  and len(to_appoints) > 0:
    #         # 判断库位状态 为 有货 且 货物type为 0【加一层判断更安全】
    #         to_index = 1
    #         if self.to_index is not None:
    #             to_index = self.to_index
    #         if self.bins.binarea[self.region_area[to_index]]['bin_list'][to_appoints[0]].goodsType == 0 and \
    #         self.bins.binarea[self.region_area[to_index]]['bin_list'][to_appoints[0]].lockId == 0:
    #             area_list = copy.deepcopy(self.region_area)
    #             area_list[to_index] = [self.region_area[self.to_index],to_appoints[0]]
    #             print("create task")
    #             asyncio.create_task(self.trace_block(area_list))
    #         return
    #     # 非设备触发的业务
    #     while True:
    #         to_send = self.const_output - sum((0 for i in self.running if i[0] == 0))
    #         for i in range(to_send):
    #             # 发单去
    #             asyncio.create_task(self.trace_block(self.region_area))
    #             # 让出CPU
    #             await asyncio.sleep(0)
    #         # 等待下一个搬运周期
    #         await asyncio.sleep(self.interval)
    #
    #
    # async def trace_block(self, area_list=None):
    #     """
    #
    #     :param area_list: [area,(area,index)]
    #     :return:
    #     """
    #     loadx,unloadx=self.from_index,self.to_index
    #     oid = "bus" + self.business_id + "type" + str(self.goods_type) + "end" + str(uuid.uuid4())
    #     count=-1
    #     loadpos=None
    #     async for pos in self.bins.get_sequence_pos_full(area_list,self.goods_type,oid,self.from_index,self.to_index,self.mode,self.region_area):
    #         if count ==-1:
    #             load=pos
    #             if load is None:
    #                 return
    #             oid = self.core.setOrder(oid, keyTask="load",keyRoute=loadpos,group=self.group,complete=False)
    #             count+=1
    #             continue
    #         current_s=await self.core.waitState(oid)
    #         if current_s==0 or current_s==3:
    #             if isinstance(pos,str):
    #                 if count == loadx:
    #                     self.core.addBlock(oid,oid+f":{count}",location=pos,operation='ForkLoad',operationArgs=self.operationArgs)
    #                 elif count == unloadx:
    #                     self.core.addBlock(oid, oid + f":{count}", location=pos, operation='ForkUnload',
    #                                        operationArgs=self.operationArgs)
    #             elif isinstance(pos,tuple):
    #                 if count==loadx:
    #                     if self.mode==1:
    #                         self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
    #                         current_s = await self.core.waitState(oid)
    #                         if current_s==0:
    #                             self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkLoad')
    #                         elif current_s > 1:
    #                             break
    #                     if self.mode==2:
    #                         self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
    #                         current_s = await self.core.waitState(oid)
    #                         if current_s == 0:
    #                             self.core.addBlock(oid, oid + f":{count}", location=pos[1], operation='ForkLoad')
    #                             current_s = await self.core.waitState(oid)
    #                             if current_s == 0:
    #                                 self.core.addBlock(oid, oid + f":{count}", location=pos[2], operation='ForkHeight')
    #                             else:
    #                                 break
    #                         else:
    #                             break
    #                 elif count==unloadx:
    #                     if self.mode==1:
    #                         self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
    #                         current_s = await self.core.waitState(oid)
    #                         if current_s==0:
    #                             self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkUnoad')
    #                         elif current_s > 1:
    #                             break
    #                     if self.mode==2:
    #                         self.core.addBlock(oid, oid + f":{count}", location=pos[0], operation='ForkHeight')
    #                         current_s = await self.core.waitState(oid)
    #                         if current_s == 0:
    #                             self.core.addBlock(oid, oid + f":{count}", location=pos[1], operation='ForkUload')
    #                             current_s = await self.core.waitState(oid)
    #                             if current_s == 0:
    #                                 self.core.addBlock(oid, oid + f":{count}", location=pos[2], operation='ForkHeight')
    #                             else:
    #                                 break
    #                         else:
    #                             break
    #         else:
    #             break
    #         count+=1
    #     self.core.markComplete(oid)


if __name__ == '__main__':
    logging.basicConfig(filename=f'log\stranger_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log',  # 设置输出文件
                        level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    # test_b.update_area(buss_area2,ifrandom=True)
    # test.update_ttheap("A",1)
    pass


    async def main():
        buss_area2 = {
            'A': [f"A-05-05-0{i}" for i in range(1, 7)]+[f"A-05-08-0{i}" for i in range(1, 7)],
        }
        buss_area3 = {
            'B': ["AP21237", "AP21233", "AP21160"]
        }
        test_b = Bins()
        test_b.update_area(buss_area2, goodsType=1)
        test_b.update_area(buss_area3, goodsType=0)
        # test_b.update_area(buss_area2, goodsType=0)
        demo = Business(1, test_b, group="",label="L1",from_areas='A', to_areas='B', vehicle_type="box", goods_type=1,const_output=6)
        tasks = []
        # tasks.append(asyncio.create_task(el1.get_through()))
        # tasks.append(asyncio.create_task(el2.get_through()))
        # tasks.append(asyncio.create_task(el3.get_through()))
        # tasks.append(asyncio.create_task(v_el2.get_through()))
        # tasks.append(asyncio.create_task(v_el1.get_through()))
        tasks.append(asyncio.create_task(demo.perform_task_load_box()))
        tasks.append(asyncio.create_task(demo.perform_task_unload_box()))
        await asyncio.gather(*tasks)

        # demo=Business(1,)
    asyncio.run(main(), debug=True)