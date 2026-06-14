Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Dimensions                                                        ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private mUnRadius As Double
Private mJ As Double
Private mDefl As Double
Private mTabDefl() As Double
Private mTabLoad() As Double
Private mAlpha As Double
Private mOmega As Double
Private mMuSlipX() As Double
Private mMuSlipY() As Double
Private mSlip As Double
Private mAccx As Double
Private mVitx As Double
Private mDepx As Double
Private mkx As Double
Private mcx As Double
Private mFSpin As Double
Private mWheelMass As Double

'''''''' Unloaded radius ''''''''''
Property Get UnRadius() As Double
' Propriété en lecture
UnRadius = mUnRadius
End Property
Property Let UnRadius(UnRadius As Double)
' Propriété en écriture
mUnRadius = UnRadius
End Property

'''''''' Defflection du pneu ''''''''''
Property Get Defl() As Double
' Propriété en lecture
Defl = mDefl
End Property
Property Let Defl(Defl As Double)
' Propriété en écriture
mDefl = Defl
End Property

'''''''' rayon effectif''''''''''
Property Get REff() As Double

'On recherche la position dans le tableau de Pos
REff = (mUnRadius - 1 / 3 * mDefl)

End Property

'''''''' Inertie ''''''''''
Property Get j() As Double
' Propriété en lecture
j = mJ
End Property
Property Let j(j As Double)
' Propriété en écriture
mJ = j
End Property

'''''''' Table deflection du pneu ''''''''''
Property Get TabDefl() As Double()
' Propriété en lecture
TabDefl = mTabDefl
End Property
Property Let TabDefl(ByRef TabDefl() As Double)
' Propriété en écriture
mTabDefl = TabDefl
End Property

'''''''' Table effort du pneu ''''''''''
Property Get TabLoad() As Double()
' Propriété en lecture
TabLoad = mTabLoad
End Property
Property Let TabLoad(ByRef TabLoad() As Double)
' Propriété en écriture
mTabLoad = TabLoad
End Property

'''''''' Section de Bh ''''''''''
Property Get FTyre() As Double

'On recherche la position dans le tableau de Pos
Dim i As Integer
If mDefl < mTabDefl()(0) Then
FTyre = mTabDefl()(0)
Else
For i = 0 To UBound(mTabDefl()) - 1
 If mDefl >= mTabDefl()(i) And mDefl < mTabDefl()(i + 1) Then
 Exit For
 End If
Next
If i < UBound(mTabDefl()) Then
FTyre = (mTabLoad()(i) + (mDefl - mTabDefl()(i)) * ((mTabLoad()(i + 1) - mTabLoad()(i)) / (mTabDefl()(i + 1) - mTabDefl()(i))))
Else
FTyre = mTabLoad()(i)
End If
End If

End Property

'''''''' Acceleration de rotation ''''''''''
Property Get Alpha() As Double
' Propriété en lecture
Alpha = mAlpha
End Property
Property Let Alpha(Alpha As Double)
' Propriété en écriture
mAlpha = Alpha
End Property
'''''''' Vitesse de rotation ''''''''''
Property Get Omega() As Double
' Propriété en lecture
Omega = mOmega
End Property
Property Let Omega(Omega As Double)
' Propriété en écriture
mOmega = Omega
End Property

'''''''' Table X mu slip ''''''''''
Property Get MuSlipX() As Double()
' Propriété en lecture
MuSlipX = mMuSlipX
End Property
Property Let MuSlipX(ByRef MuSlipX() As Double)
' Propriété en écriture
mMuSlipX = MuSlipX
End Property
'''''''' Table Y mu slip ''''''''''
Property Get MuSlipY() As Double()
' Propriété en lecture
MuSlipY = mMuSlipY
End Property
Property Let MuSlipY(ByRef MuSlipY() As Double)
' Propriété en écriture
mMuSlipY = MuSlipY
End Property

'''''''' Section de Bh ''''''''''
Property Get Mu() As Double

'On recherche la position dans le tableau de Pos
Dim i As Integer

For i = 0 To UBound(mMuSlipX()) - 1
 If Abs(mSlip) >= mMuSlipX()(i) And Abs(mSlip) < mMuSlipX()(i + 1) Then
 Exit For
 End If
Next
If i < UBound(mMuSlipX()) Then
Mu = (mMuSlipY()(i) + (Abs(mSlip) - mMuSlipX()(i)) * ((mMuSlipY()(i + 1) - mMuSlipY()(i)) / (mMuSlipX()(i + 1) - mMuSlipX()(i)))) * 0.55
Else
Mu = mMuSlipY()(i) * 0.55
End If

End Property

'''''''' Slip ''''''''''
Property Get Slip() As Double
' Propriété en lecture
Slip = mSlip
End Property
Property Let Slip(Slip As Double)
' Propriété en écriture
mSlip = Slip
End Property

'''''''' Accx ''''''''''
Property Get Accx() As Double
' Propriété en lecture
Accx = mAccx
End Property
Property Let Accx(Accx As Double)
' Propriété en écriture
mAccx = Accx
End Property

'''''''' Depx ''''''''''
Property Get Depx() As Double
' Propriété en lecture
Depx = mDepx
End Property
Property Let Depx(Depx As Double)
' Propriété en écriture
mDepx = Depx
End Property

'''''''' Vitx ''''''''''
Property Get Vitx() As Double
' Propriété en lecture
Vitx = mVitx
End Property
Property Let Vitx(Vitx As Double)
' Propriété en écriture
mVitx = Vitx
End Property

'''''''' kx ''''''''''
Property Get kx() As Double
' Propriété en lecture
kx = mkx
End Property
Property Let kx(kx As Double)
' Propriété en écriture
mkx = kx
End Property

'''''''' cx ''''''''''
Property Get cx() As Double
' Propriété en lecture
cx = mcx
End Property
Property Let cx(cx As Double)
' Propriété en écriture
mcx = cx
End Property

'''''''' FSpin ''''''''''
Property Get FSpin() As Double
' Propriété en lecture
FSpin = mFSpin
End Property
Property Let FSpin(FSpin As Double)
' Propriété en écriture
mFSpin = FSpin
End Property

'''''''' WheelMass ''''''''''
Property Get WheelMass() As Double
' Propriété en lecture
WheelMass = mWheelMass
End Property
Property Let WheelMass(WheelMass As Double)
' Propriété en écriture
mWheelMass = WheelMass
End Property

'''''''' Fx ''''''''''
Property Get Fx() As Double

'On recherche la position dans le tableau de Pos
Fx = mkx * mDepx + mcx * mVitx

End Property
