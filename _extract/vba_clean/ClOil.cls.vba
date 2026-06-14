Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Dimensions                                                        ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private mRho As Double
Private mBulk As Double
Private mVisc As Double
Private mTemp As Double

'''''''' Masse volumique ''''''''''
Property Get Rho() As Double
' Propriété en lecture
Rho = mRho
End Property
Property Let Rho(Rho As Double)
' Propriété en écriture
mRho = Rho
End Property

'''''''' Module de bulk ''''''''''
Property Get Bulk() As Double
' Propriété en lecture
Bulk = mBulk
End Property
Property Let Bulk(Bulk As Double)
' Propriété en écriture
mBulk = Bulk
End Property

'''''''' Viscosité cinématique ''''''''''
Property Get Visc() As Double
' Propriété en lecture
Visc = mVisc
End Property
Property Let Visc(Visc As Double)
' Propriété en écriture
mVisc = Visc
End Property

'''''''' Temperature ''''''''''
Property Get Temp() As Double
' Propriété en lecture
Temp = mTemp
End Property
Property Let Temp(Temp As Double)
' Propriété en écriture
mTemp = Temp
End Property
