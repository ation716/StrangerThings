import akshare

a="""{"Load":data['K'],"Unload":data['O'],"fixpoint":"LM234"}"""
b=a.strip("}").strip("{").split(",")
b.insert(0,["wait","next"])
b.insert(2,["wait","last"])
b.insert(3,["wait","next"])
b.insert(5,["wait","last"])
tt=b.pop()
tt=tt.split("\"")
b.insert(3,["wait",tt[-2]])
b[1]=b[1].replace(":",",").replace("\"","\'").split(",")
b[-2]=b[-2].replace(":",",").split(",")
# print(tt)
print(b)
