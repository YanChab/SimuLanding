Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Coordonnées dans le repère Rsol                                   ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private mAlY As Double
Private mOmY As Double
Private mThAY As Double
Private mThRY As Double
Private mJyy As Double
Private mLgAB As Double
Private mLgRB As Double
Private mLgRA As Double

Property Get AlY() As Double
' Propriété en lecture
AlY = mAlY
End Property
Property Let AlY(AlY As Double)
' Propriété en écriture
mAlY = AlY
End Property

Property Get OmY() As Double
' Propriété en lecture
OmY = mOmY
End Property
Property Let OmY(OmY As Double)
' Propriété en écriture
mOmY = OmY
End Property

Property Get ThAY() As Double
' Propriété en lecture
ThAY = mThAY
End Property
Property Let ThAY(ThAY As Double)
' Propriété en écriture
mThAY = ThAY
End Property

Property Get ThRY() As Double
' Propriété en lecture
ThRY = mThRY
End Property
Property Let ThRY(ThRY As Double)
' Propriété en écriture
mThRY = ThRY
End Property

Property Get Jyy() As Double
' Propriété en lecture
Jyy = mJyy
End Property
Property Let Jyy(Jyy As Double)
' Propriété en écriture
mJyy = Jyy
End Property

Property Get LgAB() As Double
' Propriété en lecture
LgAB = mLgAB
End Property
Property Let LgAB(LgAB As Double)
' Propriété en écriture
mLgAB = LgAB
End Property

Property Get LgRB() As Double
' Propriété en lecture
LgRB = mLgRB
End Property
Property Let LgRB(LgRB As Double)
' Propriété en écriture
mLgRB = LgRB
End Property
Property Get LgRA() As Double
' Propriété en lecture
LgRA = mLgRA
End Property
Property Let LgRA(LgRA As Double)
' Propriété en écriture
mLgRA = LgRA
End Property
