import config as cg
import requests
class SingletonMetaClass(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMetaClass, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
class CoreUtils(SingletonMetaClass):
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
