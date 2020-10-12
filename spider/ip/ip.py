#encoding=utf8
import platform

def get_windows_localip():
    import socket
    local_ip = socket.gethostbyname(socket.gethostname())#这个得到本地ip
    return local_ip

def get_linux_localip(eth="eth0"):
    import socket
    import fcntl
    import struct

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_ip = ""
    try:    
        local_ip  =  socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915, struct.pack('256s', eth[:15]))[20:24])
    except Exception, e:
        return ""
    
    return local_ip

def get_localip(name="eth"):
    local_ip = ""
    try:
        if  platform.system() == "Windows":
            local_ip =  get_windows_localip()
        else:
            for i in range(0, 10):
                local_ip =  get_linux_localip("%s%d"%(name, i))
                if local_ip != "":
                    break
                
    except Exception, e:
        local_ip = ""
    return local_ip
    
if __name__ == "__main__":
    print get_localip()
    
        
           
    