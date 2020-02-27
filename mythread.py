from threading import Thread
from sys import exit  as s_exit
from time import sleep

def split(l,n):
    n_averge=len(l)//n
    list_return=[]
    for x in range(n-1):
        list_return.append(l[x*n_averge:(x+1)*n_averge])
        
    list_return.append(l[n_averge*(n-1):])
    return list_return

def myThread(func_names=[],func_params=[], dont_join=0):
    if callable(func_names):
        func_names=[func_names for x in range(len(func_params))]
    func_n=len(func_names)
    if not func_n:
        print('Please enter functions into the func_names,the system will exit!')
        s_exit()
    threadings_n=len(func_params)
    if func_n!=1 and threadings_n !=func_n:
        print('The params\' count is not equal the functions name\'count,the system will exit!')
        s_exit()
    if func_n ==1:
        func_names=[func_names[0] for x in range(threadings_n)]
    threads=[]
    for f,p in zip(func_names,func_params):
        p=p if type(p)==tuple else tuple([p])
        if p==(None,):
            p=()
        a=Thread(target=f,args=p)
        a.start()
        threads.append(a)
    if dont_join==0:
        for x in threads:
            x.join()
    else:
        return threads
    print('The multithreading ended!')

def f(x=1,y=2):
    print(x)
    sleep(1)
    print(y)

def f1(dont_join=0):
    myThread(f,[None for x in range(5)],dont_join)
    print('Done!')
    
##myThread([f,f,f],[1,1,1])
##myThread([f1],[(1,2),(3,4),(5,6)])
##print('\n')
##myThread([f,f1],['I am F!',('I am F two!')])
