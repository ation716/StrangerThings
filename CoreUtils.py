import requests
import json
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
        # self.ip = cg.ip if ip is None else ip
        self.ip = "http://127.0.0.1:8088"
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
        """
        查询机器人容器状态 - 针对料箱车的
        :return:
        """
        r = requests.get(cg.ip + f"/robotsStatus?vehicles={vehicle}").json()
        return r['report'][0]['rbk_report']['containers']

    def get_robot_current_order(vehicle):
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