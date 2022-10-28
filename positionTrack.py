import numpy as np
from multiprocessing import Pool
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
    def __init__(self, aRef, accelRatio: float, accelDistro: float, debugFlag: bool) -> None:
        self.accelRatio = accelRatio
        self.accelDistro = accelDistro
        
#        self.aRef = np.array(aRef)
        self.aRef = np.array([aRef[1], aRef[2], [-aRef[0][0]]])

        self.debugFlag = debugFlag

        if (self.debugFlag):
            print(f'aRef:\n{self.aRef}')

    def getQInit(self, firstAccel):
        a_mag = np.sqrt(sum([i[0]**2 for i in firstAccel]))
        ak_norm = firstAccel/a_mag

        a_angle = np.arccos(sum([a*b for a,b in zip(self.aRef, ak_norm)])[0])
        a_axis = np.cross(self.aRef.T, ak_norm.T)[0]

        qTemp = chartEtoQ(chartQtoE(Quaternion(np.cos(a_angle/2), [i*np.sin(a_angle/2) for i in a_axis])))
        self.q = [qTemp]

    def batchApply(self, timeLists, accelLists, gyroLists):
        with Pool() as pool:
            poolArgs = [(timeLists[i], accelLists[i], gyroLists[i]) for i in range(len(timeLists))]
            swingRotations = pool.starmap(self.applyData, poolArgs)

        return swingRotations

    def applyData(self, timeList, accelList, gyroList):
        ak_0 = np.array([[accelList[1][0]],
                         [accelList[2][0]],
                         [-accelList[0][0]]])
        self.getQInit(ak_0)

        for i in range(0, len(timeList)-1):
            q_previous = self.q[-1]
            dt = (timeList[i+1] - timeList[i])

            #############################################
            ##             LOCAL -> WORLD              ##
            ##                 X -> -Z                 ##
            ##                 Y -> X                  ##
            ##                 Z -> Y                  ##
            #############################################

            wk = np.array([[gyroList[1][i+1] * np.pi/180],
                           [gyroList[2][i+1] * np.pi/180],
                           [-gyroList[0][i+1] * np.pi/180]])

            ak = np.array([[accelList[1][i+1]],
                           [accelList[2][i+1]],
                           [-accelList[0][i+1]]])

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

            accelList[3]

            accelProportion = self.accelRatio*np.exp(-0.5*((accelList[3][i+1]-1)/self.accelDistro)**2)
            adjusted_q = (1-accelProportion) * w_q + accelProportion * a_q

            self.q.append(chartEtoQ(chartQtoE(adjusted_q)))

            if (self.debugFlag):
                print(f'wk:\n{wk}')
                print(f'ak:\n{ak}')
                print(f'w_q: {w_q}')
                print(f'a_q: {a_q}')
                print(f'adjusted_q: {adjusted_q}')
                print(f'q: {self.q[-1]}')

        return [np.array(i.toR()) for i in self.q]
