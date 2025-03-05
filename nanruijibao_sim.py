import nanruijibao
from StrangerThings import Bins,Business,EL
import asyncio
# from biyadi import *


# 比亚迪料箱车逻辑测试
async def main():
    # 初始化库位
    bins = Bins(nanruijibao.data)
    bins.update_bin_attr({"kuqu":[0,0,0,0,True,(0,1)]})
    vehicles1=[f"CTU-2F-{i}" for i in range(1,5)]
    for i in vehicles:
        # clear containers
        requests.post(url=f'{cg.ip}/clearAllContainersGoods', json={"vehicle": i})
        # 机器人行驶速度 + 模拟充电
        res = requests.post(cg.ip + '/updateSimRobotState', json={
            "vehicle_id": i,
            "rotate_speed": 30,
            "speed": 1,
            "battery_percentage": 1,
            "charge_speed":0.005,
            "enable_battery_consumption":True,
            "no_task_battery_consumption": 0.05,
            "task_battery_consumption":0.15
        })
        replay.set_operation_time(i,operation='script', t =18)
    business1 = Business(business_id=1, region_area=["shusongxian1", "kuqu"], interval=50, const_output=5,
                    bins=bins, vehicles=vehicles1, goods_type=0)
    business2 = Business(business_id=2, region_area=["kuqu", "shoudong"], interval=50, const_output=5,
                    bins=bins,vehicles=vehicles1,goods_type=0)
    business3 = Business(business_id=3, region_area=["kuqu", "zidong"], interval=50, const_output=5,
                    bins=bins,vehicles=vehicles1, goods_type=0)
    business4 = Business(business_id=4, region_area=["shoudong", "kuqu"], interval=5,
                         bins=bins, vehicles=vehicles1,goods_type=1)
    business5 = Business(business_id=5, region_area=["zidong", "kuqu"], interval=5,
                         bins=bins, vehicles=vehicles1, goods_type=1)
    business6 = Business(business_id=5, region_area=["kuqu", "shusongxian2"], interval=5,
                         bins=bins, vehicles=vehicles1, goods_type=1)
    # 设备绑定的点位A
    data = {
        "name": '01',
        "teleport_from": "",
        "teleport_to": "",
        "origin_type": 0,
        "final_type": 1,
        "from_area": 'kuqu',
        "to_area": "kuqu",
        "bus_from": business3,
        "bus_to": business5,
        "working_time": 8,
        "changeSt": 0,
        "state": 0,
        "area":nanruijibao.data
    }
    data['teleport_from'] =["Z-01-02-01"]
    data['teleport_to'] =["Z-01-02-02"]
    data['from_area'] ='zidong'
    data['to_area'] ='zidong'
    el1 = EL(bins=bins, data=data)
    data['teleport_from'] =["Z-02-02-01"]
    data['teleport_to'] =["Z-02-02-02"]
    data['from_area'] ='zidong'
    data['to_area'] ='zidong'
    el2 = EL(bins=bins, data=data)
    data['teleport_from'] = ["Z-03-02-01"]
    data['teleport_to'] = ["Z-03-02-02"]
    data['from_area'] = 'zidong'
    data['to_area'] = 'zidong'
    el3 = EL(bins=bins, data=data)


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
    tasks = []
    tasks.append(asyncio.create_task(el1.get_through()))
    tasks.append(asyncio.create_task(el2.get_through()))
    tasks.append(asyncio.create_task(el3.get_through()))
    # tasks.append(asyncio.create_task(v_el2.get_through()))
    # tasks.append(asyncio.create_task(v_el1.get_through()))
    # tasks.append(asyncio.create_task(business1.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business1.perform_task_load_box()))
    # tasks.append(asyncio.create_task(business2.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business2.perform_task_load_box()))
    # tasks.append(asyncio.create_task(business3.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business3.perform_task_load_box()))
    # tasks.append(asyncio.create_task(business4.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business4.perform_task_load_box()))
    # tasks.append(asyncio.create_task(business5.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business5.perform_task_load_box()))
    # tasks.append(asyncio.create_task(business6.perform_task_unload_box()))
    # tasks.append(asyncio.create_task(business6.perform_task_load_box()))
    tasks.append(asyncio.create_task(bins.release_bins()))
    await asyncio.gather(*tasks)
    print("bingo")

if __name__ == '__main__':

    asyncio.run(main(),debug=True)


