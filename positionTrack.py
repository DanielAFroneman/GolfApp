import numpy as np
from quart import Quaternion

def chartEtoQ(e) -> Quaternion:
    eT = [i[0] for i in e]
    q = 1 / np.sqrt(4 + sum([i**2 for i in eT]))
    return Quaternion(2*q, [q*i for i in eT])

def chartQtoE(q: Quaternion):
    return [[2*i/q.q0] for i in q.q]

def chartGetT(q: Quaternion):
    qx = np.array([[0, -q.q[2], q.q[1]],
                   [q.q[2], 0, -q.q[0]],
                   [-q.q[1], q.q[0], 0]])
    return q.q0 * (q.q0*np.eye(3)-qx)

def EtoR(e):
    rollaA= e[0][0]
    pitchA = e[1][0]
    yawA = e[2][0]

    roll = np.array([[1, 0, 0],
                     [0, np.cos(rollaA), -np.sin(rollaA)],
                     [0, np.sin(rollaA), np.cos(rollaA)]])
    
    pitch = np.array([[np.cos(pitchA), 0, np.sin(pitchA)],
                      [0, 1, 0],
                      [-np.sin(pitchA), 0, np.cos(pitchA)]])

    yaw = np.array([[np.cos(yawA), -np.sin(yawA), 0],
                    [np.sin(yawA), np.cos(yawA), 0],
                    [0, 0, 1]])

    return np.matmul(np.matmul(yaw, pitch), roll)

class QCompFilter:
    def __init__(self, aRef, qinit: Quaternion, accelRatio: float, debugFlag: bool) -> None:
        self.accelRatio = accelRatio
        
        self.aRef = np.array(aRef)
        self.q = [qinit]

        self.debugFlag = debugFlag

        if (self.debugFlag):
            print(f'aRef:\n{self.aRef}')
            print(f'q: {self.q[0]}')

    def applyData(self, df):
        for i in range(0, len(df)-1):
            q_previous = self.q[-1]
            dt = (df.iloc[i+1]["timestamp"] - df.iloc[i]["timestamp"]) * 0.122*10**-3

            wk = np.array([[df.iloc[i+1]["gyroX"] * np.pi/180],
                           [df.iloc[i+1]["gyroY"] * np.pi/180],
                           [df.iloc[i+1]["gyroZ"] * np.pi/180]])

            ak = np.array([[df.iloc[i+1]["accelX"]],
                           [df.iloc[i+1]["accelY"]],
                           [df.iloc[i+1]["accelZ"]]])

            w_mag = np.sqrt(sum([i[0]**2 for i in wk]))
            w_angle = w_mag*dt/2

            if w_mag == 0:
                w_delta = Quaternion(np.cos(w_angle), [0.0 ,0.0 ,0.0])
            else:
                w_delta = Quaternion(np.cos(w_angle), [i[0]*np.sin(w_angle)/w_mag for i in wk])

            w_q = q_previous * w_delta

            a_mag = np.sqrt(sum([i[0]**2 for i in ak]))
            ak_norm = ak/a_mag


            a_angle = np.arccos(sum([a*b for a,b in zip(self.aRef, ak_norm)])[0])
            a_axis = np.cross(self.aRef.T, ak_norm.T)[0]

            a_q = Quaternion(np.cos(a_angle/2), [i*np.sin(a_angle/2) for i in a_axis])

            adjusted_q = (1-self.accelRatio) * w_q + self.accelRatio * a_q

            self.q.append(chartEtoQ(chartQtoE(adjusted_q)))

            if (self.debugFlag):
                print(f'wk:\n{wk}')
                print(f'ak:\n{ak}')
                print(f'w_q: {w_q}')
                print(f'a_q: {a_q}')
                print(f'adjusted_q: {adjusted_q}')
                print(f'q: {self.q[-1]}')

        return [np.array(i.toR()) for i in self.q]
