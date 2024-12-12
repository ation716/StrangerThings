import requests
import json
import uuid
from typing import Union
import asyncio
import config as cg
class SingletonMetaClass(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMetaClass, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
class CoreUtil(metaclass=SingletonMetaClass):
    """"""
    def __init__(self,ip:str=""):
        """"""
        print("init coreUtil")
        self.ip = cg.ip if not ip else ip
    def getBlockState(self,oid,name):
        """查询所有运单块状态，返回block 为完成状态且 为load，unload的状态和动作
        return [(state,op,name),]
        """
        r = requests.get(self.ip + "/orderDetails/" + oid).json()
        result=[]
        if not r.get('blocks'):
            pass
        for b in r.get('blocks'):
            if b.get('location')==name:
                if b.get('state')=="FINISHED" or b.get('state')=="STOPPED":
                    if b.get('operation') in ("ForkLoad","JackLoad"):
                        result.append((b.get('state'),'load'))
                    elif b.get('operation') in ('ForkUnload','JackUnload'):
                        result.append((b.get('state'),'unload'))
                    else:
                        if b.get('operation')=="script":
                            if b.get('script_args'):
                                if b.get('script_args').get('operation')=="load":
                                    result.append((b.get('state'), 'unload'))
                                elif b.get('script_args').get('operation')=="unload":
                                    result.append((b.get('state'), 'load'))
                break
        if r.get("state") == "STOPPED" and result==[]:
            return False
        return result

    def markComplete(self,oid:str):
        """封口"""
        return requests.post(self.ip + "/markComplete", json={"id":oid})

    def getOrderState(self,oid):
        """"""
        r = requests.get(self.ip + "/orderDetails/" + oid).json()
        if r is None:
            return False,False
        return r.get("state"),len(r.get('blocks'))

    async def waitState(self,oid):
        """状态waiting返回True，终态返回False"""
        while True:
            state,block= self.getOrderState(oid)
            if state == "WAITING":
                return 0
            elif state=="FINISHED":
                return 1
            elif state=="STOPPED":
                return 2
            elif state=="TOBEDISPATCHED" and block==0:
                return 3
            await asyncio.sleep(1)

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
                    'blockId': str(kwargs.get('goodsType'))+oid + ':01',
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

    def get_contaioners_data(self,vehicle) -> list:
        """
        查询机器人容器状态 - 针对料箱车的
        :return:
        """
        r = requests.get(cg.ip + f"/robotsStatus?vehicles={vehicle}").json()
        return r['report'][0]['rbk_report']['containers']

    def get_robot_current_order(self,vehicle):
        """
        目前来看，是针对顶升车和叉车的，查询机器人
        :return:
        """
        r = requests.get(cg.ip + f"/robotsStatus?vehicles={vehicle}").json()
        return r['report'][0]['current_order']

    def set_operation_time(self,vehicle:str,operation: Union[str,list[str]]="ForkLoad",t: Union[float,list]=10):
        """设置仿真机器人动作延迟，
        需要241129之后的版本
        """
        match operation:
            case str():
                data = {
                    'vehicle_id': vehicle,
                    'operation_time': json.dumps([{
                        'operation': operation,
                        'time': t
                    }])
                }
            case list():
                data = {
                    'vehicle_id': vehicle,
                    'operation_time': json.dumps(
                        [{'operation': op, 'time': ti} for op, ti in zip(operation, t)]
                    )
                }
            case _:
                raise TypeError('operation 参数必须为 str 或 list 类型')
        return requests.post(f"{self.ip}/updateSimRobotState", json.dumps(data)).json()

    def modifyParamNew(self, data):
        """
        新版本的core，用http设置参数
        """
        r = requests.post(self.ip+"/saveCoreParam", json = data)
        print(r.content)

    def setOrder(self, oid=None,vehicle="",location=None,complete=True,group="",keyTask="",keyRoute="",operation=""):
        if oid is None:
            oid = str(uuid.uuid4())
        if location != None:
            datas = json.dumps(
                {
                    "blocks": [
                        {
                            "blockId": oid + ":0",
                            "location": location,
                            "operation": ("" if type(operation) is not str else operation),
                        }
                    ],
                    "complete": complete,
                    "id": oid,
                    "vehicle": ("" if type(vehicle) is not str else vehicle),
                    "group": ("" if type(group) is not str else group),
                    "keyRoute": (keyRoute if isinstance(keyRoute, str) or isinstance(keyRoute, list) else ""),
                    "keyTask": ("" if type(keyTask) is not str else keyTask),
                }
            )
        else:
            datas = json.dumps(
                {
                    "blocks": [],
                    "complete": complete,
                    "id":oid,
                    "vehicle": ("" if type(vehicle) is not str else vehicle),
                    "group": ("" if type(group) is not str else group),
                    "keyRoute": ([] if type(keyRoute) is not list else keyRoute),
                    "keyTask": ("" if type(keyTask) is not str else keyTask),
                }
            )
        print(self.ip + "/setOrder")
        r = requests.post(self.ip + "/setOrder", data=datas)
        print("set_Order",r.json())
        return oid

    def addBlock(self, orderId=None, blockId=None,location=None,
                 binTask=None, operation=None, operationArgs=None,
                 scriptName=None, scriptArgs=None, goodsId=None,
                  complete=False):
        blockId = str(uuid.uuid4) if blockId is None else blockId
        datas = {
            "blocks": [
                {
                    "blockId": blockId,
                    "location": location,
                    "binTask": ("" if type(binTask) is not str else binTask),
                    "operation": ("" if type(operation) is not str else operation),
                    "operationArgs": ("" if type(operationArgs) is not dict else operationArgs),
                    "scriptName": ("" if type(scriptName) is not str else scriptName),
                    "scriptArgs": ("" if type(scriptArgs) is not dict else scriptArgs),
                    "goodsId": ("" if type(goodsId) is not str else goodsId)
                }
            ],
            "id": orderId,
        }
        if complete == True:
            datas["complete"] = True
        datas = json.dumps(datas)
        r = requests.post(self.ip + "/addBlocks", data=datas)
        return blockId


if __name__ == '__main__':
    tes=CoreUtil()
    print(tes.getBlockState('9af64c43-06d2-4325-a405-46e75c76bd3b'))