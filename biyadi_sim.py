import biyadi
from StrangerThings import Bins,Business
import asyncio
# from biyadi import *


# 比亚迪料箱车逻辑测试
async def main():
    # 初始化库位
    bins = Bins(biyadi.data)
    bins.update_bin_attr(biyadi.init_goods)

    vehicles1=[f"container-X-0{i}" for i in range(1,5)]
    vehicles2=["container-D-03" , "container-D-06"]
    business1 = Business(business_id=1, region_area=["ds_0", "ds_1"], interval=50, const_output=5,
                    bins=bins, vehicles=vehicles1, goods_type=1)
    business2 = Business(business_id=2, region_area=["ds_0", "ds_3"], interval=50, const_output=5,
                    bins=bins, goods_type=1)
    business3 = Business(business_id=3, region_area=["ds_1", "ds_2"], interval=50, const_output=5,
                    bins=bins, goods_type=1)
    business4 = Business(business_id=4, region_area=["ds_3", "ds_4"], interval=5,
                         bins=bins, goods_type=2)
    business5 = Business(business_id=5, region_area=["box_north_0", "box_north_1"], interval=5,
                         bins=bins, vehicles=vehicles2, goods_type=2)
    business6 = Business(business_id=5, region_area=["box_north_0", "box_north_1"], interval=5,
                         bins=bins, vehicles=vehicles2, goods_type=2)
    business7 = Business(business_id=5, region_area=["box_north_0", "box_north_1"], interval=5,
                         bins=bins, vehicles=vehicles2, goods_type=2)
    business8 = Business(business_id=5, region_area=["box_north_0", "box_north_1"], interval=5,
                         bins=bins, vehicles=vehicles2, goods_type=2)
    # # 设备绑定的点位A
    # data = {
    #     "name": '01',
    #     "teleport_from": "",
    #     "teleport_to": "",
    #     "origin_type": 1,
    #     "final_type": 2,
    #     "from_area": 'L1',
    #     "to_area": "L2",
    #     "bus_from": 3,
    #     "bus_to": 4,
    #     "working_time": 60,
    #     "changeSt": 0,
    #     "state": 0,
    #     "area":biyadi
    # }
    # data['teleport_from'] =["DHQ-01"]
    # data['teleport_to'] =["DHQ-02"]
    # el1 = EL(bins=bins, data=data)
    # data['teleport_from'] =["DHQ-03"]
    # data['teleport_to'] =["DHQ-04"]
    # el2 = EL(bins=bins, data=data)
    # data['teleport_from'] = ["DHQ-05"]
    # data['teleport_to'] = ["DHQ-06"]
    # el3 = EL(bins=bins, data=data)
    # data['teleport_from'] = biyadi.get("J")
    # data['teleport_to'] = biyadi.get("K")
    # data['working_time'] = 30
    # data['bus_from'] = ''
    # data['bus_to']=''
    # data['final_type']=1
    # v_el1= EL(bins=bins, data=data)
    # data['teleport_from'] = biyadi.get("M")
    # data['teleport_to'] = biyadi.get("N")
    # data['final_type'] = 2
    # data['origin_type'] = 2
    #
    # v_el2 = EL(bins=bins, data=data)
    # tasks = []
    # # tasks.append(asyncio.create_task(el1.get_through()))
    # # tasks.append(asyncio.create_task(el2.get_through()))
    # # tasks.append(asyncio.create_task(el3.get_through()))
    # # tasks.append(asyncio.create_task(v_el2.get_through()))
    # # tasks.append(asyncio.create_task(v_el1.get_through()))
    # tasks.append(asyncio.create_task(business1.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business1.perform_task_load_box()))
    # tasks.append(asyncio.create_task(bins.release_bins()))
    # await asyncio.gather(*tasks)
    print("bingo")

if __name__ == '__main__':

    asyncio.run(main(),debug=True)

    print("bingo")
    pass