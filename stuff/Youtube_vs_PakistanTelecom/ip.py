from ipaddress import ip_address, IPv4Address 
  
def validIPv4(IP: str) -> str: 
    try: 
        return True if type(ip_address(IP)) is IPv4Address else False
    except ValueError: 
        return "Invalid"
  
if __name__ == '__main__' :   
        
    # Enter the Ip address  
    Ip = "192.168.0.1"
    print(validIPv4(Ip))  
  
    Ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    print(validIPv4(Ip))  
  
    Ip = "256.32.555.5"
    print(validIPv4(Ip))   
  
    Ip = "250.32:555.5"
    print(validIPv4(Ip)) 