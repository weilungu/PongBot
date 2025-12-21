import network,time,BlynkLib
from machine import Pin,PWM
from umqtt.simple import MQTTClient
import gc

gc.collect()

WIFI = [{"ssid": "shepherd", "password": "Good@11255"},
        {"ssid": "aron", "password": "00000000"},]

# SSID="aron"
# PASS="00000000"
AUTH="O-npu_Lj5Kh2v_oyBF67kAcskwlxuKx6"
MQTT_BROKER="broker.hivemq.com"
MQTT_CLIENT="pongBot"
BALL_PIN=5
MA1,MA2,MAPWM=5,4,14
MB1,MB2,MBPWM=12,13,15
SERVO_PIN=0
LONG_T=3000
HOLD_T=3000
GAUGE_INT=30
SERVO_MAP=[0,30,50,70,90,100]

ps10=None
ip10=False
it10=False
te10=None
ps12=None
ip12=False
it12=False
te12=None
blynk=None
dm=None
sp=None
sr=False
ss=0
mqtt=None

class DCMotor:
    def __init__(self,i1,i2,pw,f=1000):
        self.i1=Pin(i1,Pin.OUT)
        self.i2=Pin(i2,Pin.OUT)
        self.pw=PWM(Pin(pw))
        self.pw.freq(f)
        self.r=False
        self.s=0
        self.stop()
    def forward(self,s=100):
        s=max(0,min(100,s))
        self.i1.value(1)
        self.i2.value(0)
        self.pw.duty(int(s*1023/100))
        self.r=True
        self.s=s
    def stop(self):
        self.i1.value(0)
        self.i2.value(0)
        self.pw.duty(0)
        self.r=False
    def set_speed(self,s):
        s=max(0,min(100,s))
        self.s=s
        if self.r:
            self.pw.duty(int(s*1023/100))

class DualMotor:
    def __init__(self,a1,a2,ap,b1,b2,bp,f=1000):
        self.ma=DCMotor(a1,a2,ap,f)
        self.mb=DCMotor(b1,b2,bp,f)
    def stop(self):
        self.ma.stop()
        self.mb.stop()

def init_servo():
    global sp
    sp=PWM(Pin(SERVO_PIN,Pin.OUT),freq=50,duty=0)

def set_servo(s):
    sp.duty(int((1.5+(-s/100))*51.2))

def mqtt_callback(topic,msg):
    global blynk,ss,sr
    print("MQTT recv:",topic)
    if topic==b"pongBot/save/successful" and blynk:
        payload=msg.decode().strip()
        if payload=="TRUE":
            blynk.virtual_write(14,"True")
        else:
            blynk.virtual_write(14,"False")
    elif topic==b"pongBot/importing/successful" and blynk:
        payload=msg.decode().strip()
        if payload=="T":
            blynk.virtual_write(15,"True")
        else:
            blynk.virtual_write(15,"False")
    elif topic==b"pongBot/importing/data" and blynk:
        print("Recv import data")
        try:
            payload=msg.decode().strip()
            print("Data:",payload)
            data_dict={}
            payload=payload.strip('"')
            pairs=payload.strip('{}').split(',')
            for pair in pairs:
                if ':' in pair:
                    key,val=pair.split(':',1)
                    key=key.strip().strip('"')
                    val=val.strip().strip('"')
                    data_dict[key]=int(val)
            if 'servo_level' in data_dict:
                v1_val=data_dict['servo_level']
                if 1<=v1_val<=5:
                    ss=SERVO_MAP[v1_val]
                    blynk.virtual_write(1,v1_val)
                    if sr:
                        set_servo(ss)
            if 'motor_top' in data_dict:
                v3_val=data_dict['motor_top']
                if 1<=v3_val<=100:
                    dm.ma.set_speed(v3_val*0.5)
                    blynk.virtual_write(3,v3_val)
            if 'motor_bottom' in data_dict:
                v4_val=data_dict['motor_bottom']
                if 1<=v4_val<=100:
                    dm.mb.set_speed(v4_val*0.5)
                    blynk.virtual_write(4,v4_val)
            print("Import done")
        except Exception as e:
            print("Import err:",e)

def conn_mqtt():
    global mqtt
    try:
        mqtt=MQTTClient(MQTT_CLIENT,MQTT_BROKER)
        mqtt.set_callback(mqtt_callback)
        mqtt.connect()
        mqtt.subscribe(b"pongBot/save/successful")
        mqtt.subscribe(b"pongBot/importing/data")
        mqtt.subscribe(b"pongBot/importing/successful")
        print("MQTT OK")
        return True
    except:
        print("MQTT Fail")
        return False

def conn_wifi():
    w=network.WLAN(network.STA_IF)
    w.active(True)
    if not w.isconnected():
        for wifi in WIFI:
            print(f"WiFi...{wifi['ssid']}")
            w.connect(wifi['ssid'],wifi['password'])
            t=20
            while not w.isconnected() and t>0:
                time.sleep(1)
                t-=1
            if w.isconnected():
                print(f"WiFi OK: {wifi['ssid']}")
                return True
            print(f"Fail: {wifi['ssid']}")
        return False
    return True

def get_ms():
    try:
        return time.ticks_ms()
    except:
        return int(time.time()*1000)

def proc_btn(bp,gp,lp,ip,ps,it,te):
    now=get_ms()
    if ip and ps:
        e=now-ps
        if e%GAUGE_INT<30 and blynk:
            blynk.virtual_write(gp,min(100,int(e*100/LONG_T)))
        if e>=LONG_T and not it:
            Pin(BALL_PIN,Pin.OUT).on()
            if blynk:
                blynk.virtual_write(bp,1)
            if mqtt:
                try:
                    if bp==10:
                        v1_level=0
                        for i in range(1,6):
                            if SERVO_MAP[i]==ss:
                                v1_level=i
                                break
                        v3_panel=int(dm.ma.s*2)
                        v4_panel=int(dm.mb.s*2)
                        mqtt.publish(b"pongBot/servo/level",str(v1_level).encode())
                        mqtt.publish(b"pongBot/motor/top",str(v3_panel).encode())
                        mqtt.publish(b"pongBot/motor/bottom",str(v4_panel).encode())
                    elif bp==12:
                        print("V12 MQTT pub")
                        mqtt.publish(b"pongBot/importing",b"AAA")
                        print("V12 sent AAA")
                except Exception as e:
                    print("V12 err:",e)
            it=True
            te=now
    if it and te and now-te>=HOLD_T:
        Pin(BALL_PIN,Pin.OUT).off()
        if blynk:
            blynk.virtual_write(gp,0)
            blynk.virtual_write(bp,0)
        ip=False
        ps=None
        it=False
        te=None
    return ip,ps,it,te

def proc_all():
    global ps10,ip10,it10,te10,ps12,ip12,it12,te12
    ip10,ps10,it10,te10=proc_btn(10,11,14,ip10,ps10,it10,te10)
    ip12,ps12,it12,te12=proc_btn(12,13,15,ip12,ps12,it12,te12)

def reset_labels():
    if blynk:
        blynk.virtual_write(14,"False")
        blynk.virtual_write(15,"False")

def setup():
    global blynk,dm,sr,ss,ip10,ps10,it10,ip12,ps12,it12
    
    @blynk.on("V0")
    def v0(v):
        global sr,ss
        sr=v[0]=="1"
        if sr and ss==0:
            ss=SERVO_MAP[1]
        set_servo(ss if sr else 0)
        reset_labels()
    
    @blynk.on("V1")
    def v1(v):
        global ss
        l=int(v[0])
        if 1<=l<=5:
            ss=SERVO_MAP[l]
            if sr:set_servo(ss)
        reset_labels()
    
    @blynk.on("V2")
    def v2(v):
        if v[0]=="1":
            sa=dm.ma.s if dm.ma.s>0 else 0.5
            sb=dm.mb.s if dm.mb.s>0 else 0.5
            dm.ma.forward(sa)
            dm.mb.forward(sb)
        else:
            dm.stop()
        reset_labels()
    
    @blynk.on("V3")
    def v3(v):
        pv=int(v[0])
        if 1<=pv<=100:
            dm.ma.set_speed(pv*0.5)
        reset_labels()
    
    @blynk.on("V4")
    def v4(v):
        pv=int(v[0])
        if 1<=pv<=100:
            dm.mb.set_speed(pv*0.5)
        reset_labels()
    
    @blynk.on("V10")
    def v10(v):
        global ip10,ps10,it10
        if v[0]=="1":
            if not ip10:
                ip10=True
                ps10=get_ms()
                if blynk:
                    blynk.virtual_write(11,0)
                    blynk.virtual_write(10,0)
        else:
            if ip10 and not it10:
                ip10=False
                ps10=None
                if blynk:blynk.virtual_write(11,0)
            elif it10:
                ip10=False
                if blynk:blynk.virtual_write(10,1)
    
    @blynk.on("V12")
    def v12(v):
        global ip12,ps12,it12
        if v[0]=="1":
            if not ip12:
                ip12=True
                ps12=get_ms()
                if blynk:
                    blynk.virtual_write(13,0)
                    blynk.virtual_write(12,0)
        else:
            if ip12 and not it12:
                ip12=False
                ps12=None
                if blynk:blynk.virtual_write(13,0)
            elif it12:
                ip12=False
                if blynk:blynk.virtual_write(12,1)
    
    @blynk.on("connected")
    def conn():
        global ss
        print("Blynk OK")
        blynk.virtual_write(0,0)
        blynk.virtual_write(1,1)
        ss=SERVO_MAP[1]
        blynk.virtual_write(2,0)
        blynk.virtual_write(3,1)
        dm.ma.set_speed(0.5)
        blynk.virtual_write(4,1)
        dm.mb.set_speed(0.5)
        for p in [10,11,12,13]:
            blynk.virtual_write(p,0)
        blynk.virtual_write(14,"False")
        blynk.virtual_write(15,"False")
    
    @blynk.on("disconnected")
    def disc():
        print("Lost")

def main():
    global blynk,dm
    print("Start")
    while not conn_wifi():
        time.sleep(5)
    dm=DualMotor(MA1,MA2,MAPWM,MB1,MB2,MBPWM)
    init_servo()
    conn_mqtt()
    gc.collect()
    print("Blynk...")
    try:
        blynk=BlynkLib.Blynk(AUTH,insecure=True)
    except Exception as e:
        print(e)
        return
    setup()
    print("Ready")
    try:
        while True:
            blynk.run()
            if mqtt:
                try:
                    mqtt.check_msg()
                except:
                    pass
            proc_all()
            time.sleep(0.01)
    except:
        pass
    finally:
        dm.stop()
        set_servo(0)
        if mqtt:
            try:
                mqtt.disconnect()
            except:
                pass

if __name__=="__main__":
    main()
