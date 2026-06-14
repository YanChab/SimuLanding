Option Explicit

Private mTorDes As String
Private mRsolX As Double
Private mRsolY As Double
Private mRsolZ As Double
Private mRsolL As Double
Private mRsolM As Double
Private mRsolN As Double

Private mRlgX As Double
Private mRlgY As Double
Private mRlgZ As Double
Private mRlgL As Double
Private mRlgM As Double
Private mRlgN As Double

Property Get TorDes() As String
' Propriété en lecture
TorDes = mTorDes
End Property
Property Let TorDes(TorDes As String)
' Propriété en écriture
mTorDes = TorDes
End Property
Property Get RsolX() As Double
' Propriété en lecture
RsolX = mRsolX
End Property
Property Let RsolX(RsolX As Double)
' Propriété en écriture
mRsolX = RsolX
End Property
Property Get RsolY() As Double
' Propriété en lecture
RsolY = mRsolY
End Property
Property Let RsolY(RsolY As Double)
' Propriété en écriture
mRsolY = RsolY
End Property
Property Get RsolZ() As Double
' Propriété en lecture
RsolZ = mRsolZ
End Property
Property Let RsolZ(RsolZ As Double)
' Propriété en écriture
mRsolZ = RsolZ
End Property

Property Get RsolL() As Double
' Propriété en lecture
RsolL = mRsolL
End Property
Property Let RsolL(RsolL As Double)
' Propriété en écriture
mRsolL = RsolL
End Property
Property Get RsolM() As Double
' Propriété en lecture
RsolM = mRsolM
End Property
Property Let RsolM(RsolM As Double)
' Propriété en écriture
mRsolM = RsolM
End Property
Property Get RsolN() As Double
' Propriété en lecture
RsolN = mRsolN
End Property
Property Let RsolN(RsolN As Double)
' Propriété en écriture
mRsolN = RsolN
End Property

Property Get RlgX() As Double
' Propriété en lecture
RlgX = mRlgX
End Property
Property Let RlgX(RlgX As Double)
' Propriété en écriture
mRlgX = RlgX
End Property
Property Get RlgY() As Double
' Propriété en lecture
RlgY = mRlgY
End Property
Property Let RlgY(RlgY As Double)
' Propriété en écriture
mRlgY = RlgY
End Property
Property Get RlgZ() As Double
' Propriété en lecture
RlgZ = mRlgZ
End Property
Property Let RlgZ(RlgZ As Double)
' Propriété en écriture
mRlgZ = RlgZ
End Property

Property Get RlgL() As Double
' Propriété en lecture
RlgL = mRlgL
End Property
Property Let RlgL(RlgL As Double)
' Propriété en écriture
mRlgL = RlgL
End Property
Property Get RlgM() As Double
' Propriété en lecture
RlgM = mRlgM
End Property
Property Let RlgM(RlgM As Double)
' Propriété en écriture
mRlgM = RlgM
End Property
Property Get RlgN() As Double
' Propriété en lecture
RlgN = mRlgN
End Property
Property Let RlgN(RlgN As Double)
' Propriété en écriture
mRlgN = RlgN
End Property

Public Sub moins(tor As cTorseur)

mRsolX = -tor.RsolX
mRsolY = -tor.RsolY
mRsolZ = -tor.RsolZ
mRsolL = -tor.RsolL
mRsolM = -tor.RsolM
mRsolN = -tor.RsolN
mRlgX = -tor.RlgX
mRlgY = -tor.RlgY
mRlgZ = -tor.RlgZ
mRlgL = -tor.RlgL
mRlgM = -tor.RlgM
mRlgN = -tor.RlgN

End Sub
