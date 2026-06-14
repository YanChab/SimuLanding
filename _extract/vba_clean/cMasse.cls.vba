Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Dimensions                                                        ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private ma_gr As Double
Private ma_lg As Double
Private mv_gr As Double
Private mv_lg As Double
Private md_gr As Double
Private md_lg As Double

'''''''' Accélération par rapport au ground ''''''''''
Property Get a_gr() As Double
' Propriété en lecture
a_gr = ma_gr
End Property
Property Let a_gr(a_gr As Double)
' Propriété en écriture
ma_gr = a_gr
End Property
'''''''' Accélération par rapport au landing gear ''''''''''
Property Get a_lg() As Double
' Propriété en lecture
a_lg = ma_lg
End Property
Property Let a_lg(a_lg As Double)
' Propriété en écriture
ma_lg = a_lg
End Property

'''''''' Vitesse par rapport au ground ''''''''''
Property Get v_gr() As Double
' Propriété en lecture
v_gr = mv_gr
End Property
Property Let v_gr(v_gr As Double)
' Propriété en écriture
mv_gr = v_gr
End Property
'''''''' Vitesse par rapport au landing gear ''''''''''
Property Get v_lg() As Double
' Propriété en lecture
v_lg = mv_lg
End Property
Property Let v_lg(v_lg As Double)
' Propriété en écriture
mv_lg = v_lg
End Property
