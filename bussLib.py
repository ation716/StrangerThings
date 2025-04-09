from binLib import Bins



class Business:
    """业务"""

    def __init__(self, business_id: int, bins: Bins=None, from_area:str="",to_area:str="",group:str="",label:str="",vehicle_type:str="",goods_type: int=0,
                 from_index: Union[int, str] = 0, to_index: Union[int, str] = 1, group=None, interval=1, const_output=1,
                 mode=0):
        """
        :param business_id: int 业务id
        :param bins: 库区对象
        :param from_area: 搬运区域
        :param to_area: 取货区域
        :param group: 这些业务需要由些组完成， 料箱车需要跟踪料箱车信息
        :param label: 业务需要具有哪些标签的机器人弯成
        :param vehicle_type: 车体类型, 辅助指定动作
        :param goods_type: 取货的货物类型
        :param interval: 发单间隔等同于生产环境中机器的生产节拍
        :param const_output: 每次需要发单数量，等同于生产环境中机器每次的产量  # note 避免太多未完成运单累计，已下发未完成的不能超过const_output
        :param mode: 库位的动作模式 0 直接到库位，1 前置点库位， 2 前置点-库位-前置点
        """
        self.business_id = str(business_id)
        self.from_area = from_area
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
