import numpy as np

class Quaternion:
    def __init__(self, q0, q) -> None:
        self.q0 = q0
        self.q = q

    def __rmul__(self, other) -> 'Quaternion':
        if (isinstance(other, float) or isinstance(other, int)):
            return Quaternion(self.q0*other, [i*other for i in self.q])
        raise Exception(f"Cannot multiply <class 'Quaternion'> with {type(other)}")

    def __mul__(self, other) -> 'Quaternion':
        if (isinstance(other, Quaternion)):
            q0 = self.q0*other.q0 -  sum([x*y for x,y in zip(self.q, other.q)])
            q_1 = [self.q0*i for i in other.q]
            q_2 = [other.q0*i for i in self.q]
            q_3 = np.cross(self.q, other.q)
            return Quaternion(q0, [a+b+c for a,b,c in zip(q_1, q_2, q_3)])
        if (isinstance(other, float) or isinstance(other, int)):
            return other*self

    def __add__(self, other):
        if (isinstance(other, Quaternion)):
            q0 = self.q0 + other.q0
            q = [a+b for a,b in zip(self.q, other.q)]
            return Quaternion(q0, q)
        raise Exception(f"Cannot add <class 'Quaternion'> with {type(other)}")

    def __str__(self) -> str:
        return f'[{self.q0}, {self.q[0]}, {self.q[1]}, {self.q[2]}]'

    def conj(self) -> 'Quaternion':
        return Quaternion(self.q0, [i*-1 for i in self.q])

    def toR(self):
        return [[1-2*self.q[1]**2-2*self.q[2]**2, 2*(self.q[0]*self.q[1]-self.q[2]*self.q0), 2*(self.q[0]*self.q[2]+self.q[1]*self.q0)],
                [2*(self.q[0]*self.q[1]+self.q[2]*self.q0), 1-2*self.q[0]**2-2*self.q[2]**2, 2*(self.q[1]*self.q[2]-self.q[0]*self.q0)],
                [2*(self.q[0]*self.q[2]-self.q[1]*self.q0), 2*(self.q[1]*self.q[2]+self.q[0]*self.q0), 1-2*self.q[0]**2-2*self.q[1]**2]]

    def toEular(self):
        eularAngles = []

        sinr_cosp = 2 * (self.q0 * self.q[0] + self.q[1] * self.q[2])
        cosr_cosp = 1 - 2 * (self.q[0] * self.q[0] + self.q[1] * self.q[1])
        eularAngles.append(np.arctan2(sinr_cosp, cosr_cosp))

        sinp = 2 * (self.q0 * self.q[1] - self.q[2] * self.q[0])
        if (abs(sinp) >= 1):
            eularAngles.append(np.copysign(np.pi / 2, sinp))
        else:
            eularAngles.append(np.arcsin(sinp))

        siny_cosp = 2 * (self.q0 * self.q[2] + self.q[0] * self.q[1])
        cosy_cosp = 1 - 2 * (self.q[1] * self.q[1] + self.q[2] * self.q[2])
        eularAngles.append(np.arctan2(siny_cosp, cosy_cosp))

        return eularAngles

    def rotateVector(self, vector):
        q = Quaternion(0, vector)
        rq = self * q * self.conj()
        return rq.q
