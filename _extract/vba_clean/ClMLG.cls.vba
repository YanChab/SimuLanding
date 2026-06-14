Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Dimensions                                                        ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private mDp As Double
Private mDpis As Double
Private mDbh As Double
Private mDt As Double
Private mC As Double
Private mVh As Double
Private mVtot As Double
Private mVgbp As Double
Private mVghp As Double
Private mVginitbp As Double
Private mVginithp As Double
Private mPinitbp As Double
Private mPinithp As Double
Private mPg As Double
Private mPgtamp As Double
Private mDeltaPc As Double
Private mDeltaPd As Double
Private mDeltaPbh As Double
Private mDeltaPdalim As Double
Private ma As Double
Private mv As Double
Private md As Double
Private mQc As Double
Private mQbh As Double
Private mQp As Double
Private mQpl As Double
Private mTabPosBh() As Double
Private mTabSecBh() As Double
Private mDTrouPis As Double
Private mNbTrouPis As Double
Private mNbRealPis As Double
Private mLRealPis As Double
Private mHRealPis As Double
Private mDTrouDiap As Double
Private mNbTrouDiap As Double
Private mASeal As Double
Private mfc As Double
Private mfh As Double
Private mCoeffAtte As Double
Private mXGb As Double
Private mXGt As Double
Private mXR As Double
Private mOilBulk As Double
Private mDInsideBh As Double
Private mDIntTub As Double
Private mDMetVal As Double
Private mLMetVal As Double
Private mcMetVal As Double
Private mEntraxeInit As Double
Private mEntraxe As Double
Private mLbh As Double
Private mDintbh As Double
Private mHauteurPisBh As Double
Private mGamma As Double
Private mPrecision As Double

'''''''' Diamètre de interne de tige ''''''''''
Property Get Dp() As Double
' Propriété en lecture
Dp = mDp
End Property
Property Let Dp(Dp As Double)
' Propriété en écriture
mDp = Dp
End Property
'''''''' Diamètre de piston ''''''''''
Property Get Dpis() As Double
' Propriété en lecture
Dpis = mDpis
End Property
Property Let Dpis(Dpis As Double)
' Propriété en écriture
mDpis = Dpis
End Property

'''''''' Diamètre de BH ''''''''''

Property Get Dbh() As Double
' Propriété en lecture
Dbh = mDbh
End Property
Property Let Dbh(Dbh As Double)
' Propriété en écriture
mDbh = Dbh
End Property

'''''''' Diamètre de tige ''''''''''
Property Get Dt() As Double
' Propriété en lecture
Dt = mDt
End Property
Property Let Dt(Dt As Double)
' Propriété en écriture
mDt = Dt
End Property

'''''''' Course totale ''''''''''
Property Get c() As Double
' Propriété en lecture
c = mC
End Property
Property Let c(c As Double)
' Propriété en écriture
mC = c
End Property

'''''''' Volume huile ''''''''''
Property Get Vh() As Double
' Propriété en lecture
Vh = mVh
End Property
Property Let Vh(Vh As Double)
' Propriété en écriture
mVh = Vh
End Property
'''''''' Volume total ''''''''''
Property Get Vtot() As Double
' Propriété en lecture
Vtot = mVtot
End Property
Property Let Vtot(Vtot As Double)
' Propriété en écriture
mVtot = Vtot
End Property

'''''''' Volume gaz bp ''''''''''
Property Get Vgbp() As Double
' Propriété en lecture
Vgbp = mVgbp
End Property
Property Let Vgbp(Vgbp As Double)
' Propriété en écriture
mVgbp = Vgbp
End Property
'''''''' Volume gaz hp ''''''''''
Property Get Vghp() As Double
' Propriété en lecture
Vghp = mVghp
End Property
Property Let Vghp(Vghp As Double)
' Propriété en écriture
mVghp = Vghp
End Property
'''''''' Volume gaz init bp ''''''''''
Property Get Vginitbp() As Double
' Propriété en lecture
Vginitbp = mVginitbp
End Property
Property Let Vginitbp(Vginitbp As Double)
' Propriété en écriture
mVginitbp = Vginitbp
End Property
'''''''' Volume gaz init hp ''''''''''
Property Get Vginithp() As Double
' Propriété en lecture
Vginithp = mVginithp
End Property
Property Let Vginithp(Vginithp As Double)
' Propriété en écriture
mVginithp = Vginithp
End Property

'''''''' Pression initiale bp ''''''''''
Property Get Pinitbp() As Double
' Propriété en lecture
Pinitbp = mPinitbp
End Property
Property Let Pinitbp(Pinitbp As Double)
' Propriété en écriture
mPinitbp = Pinitbp
End Property
'''''''' Pression initiale hp ''''''''''
Property Get Pinithp() As Double
' Propriété en lecture
Pinithp = mPinithp
End Property
Property Let Pinithp(Pinithp As Double)
' Propriété en écriture
mPinithp = Pinithp
End Property
'''''''' Section compression ''''''''''
Property Get Sc() As Double
' Propriété en lecture
Sc = (mDpis * mDpis - mDbh * mDbh) * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Section detente ''''''''''
Property Get Sd() As Double
' Propriété en lecture
Sd = (mDpis * mDpis - mDt * mDt) * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Section compensation ''''''''''
Property Get Scomp() As Double
' Propriété en lecture
Scomp = (mDp * mDp) * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Section tige ''''''''''
Property Get St() As Double
' Propriété en lecture
St = mDt * mDt * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Section bh ''''''''''
Property Get Sbh() As Double
' Propriété en lecture
Sbh = mDbh * mDbh * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Pression de gaz ''''''''''
Property Get Pg() As Double
' Propriété en lecture
If md <> 0 Then
'Pg = mPinit * Application.WorksheetFunction.Power((mVgbp / (mVgbp - (md * St) + (mVh * mPgtamp / mOilBulk))), 1.4)

Dim neq As Integer
neq = 2
Dim xRes() As Double
ReDim xRes(neq) '0: DeltaPc, 1: Qbh, 2: Qp
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim i As Integer
Dim k As Integer
Dim j As Integer
Dim Pi As Double

Pi = Application.WorksheetFunction.Pi

xRes(0) = mVginitbp - mVgbp
xRes(1) = mVginithp - mVghp
xRes(2) = mPgtamp

For i = 0 To 3
f(0) = md * St - (mVh * mPgtamp / mOilBulk) - xRes(0) - xRes(1) * (Atn(0.02 * (xRes(2) - mPinithp)) + Pi / 2) * 1 / Pi
f(1) = xRes(2) * Application.WorksheetFunction.Power(mVginitbp - xRes(0), mGamma) - mPinitbp * Application.WorksheetFunction.Power(mVginitbp, mGamma)
f(2) = xRes(2) * Application.WorksheetFunction.Power(mVginithp - xRes(1), mGamma) - mPinithp * Application.WorksheetFunction.Power(mVginithp, mGamma)
mPrecision = f(0) + f(1) + f(2)
df(0, 0) = -1: df(0, 1) = -(Atn(0.02 * (xRes(2) - mPinithp)) + Pi / 2) * 1 / Pi: df(0, 2) = -xRes(1) / Pi * (0.02 / (1 + (0.02 * (xRes(2) - mPinithp)) ^ 2))
df(1, 0) = -xRes(2) * mGamma * Application.WorksheetFunction.Power(mVginitbp - xRes(0), mGamma - 1): df(1, 1) = 0: df(1, 2) = Application.WorksheetFunction.Power(mVginitbp - xRes(0), mGamma)
df(2, 0) = 0: df(2, 1) = -xRes(2) * mGamma * Application.WorksheetFunction.Power(mVginithp - xRes(1), mGamma - 1): df(2, 2) = Application.WorksheetFunction.Power(mVginithp - xRes(1), mGamma)

'inversion de la matrice
det = Application.WorksheetFunction.MDeterm(df)

If det = 0 Then
    MsgBox ("le déterminant est nul")
    Else
    invdf = Application.WorksheetFunction.MInverse(df)
End If

'Calcul des inconnues:
    For k = 0 To neq
        For j = 0 To neq
            xRes(k) = xRes(k) - invdf(k + 1, j + 1) * f(j)
        Next
    Next

 mVgbp = mVginitbp - xRes(0)
mVghp = mVginithp - xRes(1)
 Pg = xRes(2)

Next

Else
Pg = mPinitbp
End If
End Property
Property Let Pgtamp(Pgtamp As Double)
' Propriété en écriture
mPgtamp = Pgtamp
End Property

'''''''' DeltaP compression/compensation ''''''''''
Property Get DeltaPc() As Double
' Propriété en lecture
DeltaPc = mDeltaPc
End Property
Property Let DeltaPc(DeltaPc As Double)
' Propriété en écriture
mDeltaPc = DeltaPc
End Property

'''''''' DeltaP BH ''''''''''
Property Get DeltaPd() As Double
' Propriété en lecture
DeltaPd = mDeltaPd
End Property
Property Let DeltaPd(DeltaPd As Double)
' Propriété en écriture
mDeltaPd = DeltaPd
End Property
'''''''' DeltaP dans le trou cetral de la BH ''''''''''
Property Get DeltaPbh() As Double
' Propriété en lecture
DeltaPbh = mDeltaPbh
End Property
Property Let DeltaPbh(DeltaPbh As Double)
' Propriété en écriture
mDeltaPbh = DeltaPbh
End Property
'''''''' DeltaP dans la réalim de la détente ''''''''''
Property Get DeltaPdalim() As Double
' Propriété en lecture
DeltaPdalim = mDeltaPdalim
End Property
Property Let DeltaPdalim(DeltaPdalim As Double)
' Propriété en écriture
mDeltaPdalim = DeltaPdalim
End Property

'''''''' Pression compression ''''''''''
Property Get Pc() As Double
' Propriété en lecture
Pc = Pg + mDeltaPc

End Property

'''''''' Pression détente ''''''''''
Property Get Pd() As Double
' Propriété en lecture
Pd = Pc - mDeltaPd

End Property

'''''''' Effort total ''''''''''
Property Get Ftot() As Double
' Propriété en lecture
If md >= 0 Then
    If md <= mC Then
        Ftot = Sc * Pc - Sd * Pd + Sbh * Pg + FFriJoi '+ FFriBag
    Else
        Ftot = Sc * Pc - Sd * Pd + Sbh * Pg + (md - mC) * 100000000 + FFriJoi '+ FFriBag
    End If
Else
    Ftot = Sc * Pc - Sd * Pd + Sbh * Pg + md * 100000000 + FFriJoi  '+ FFriBag
End If

End Property

'''''''' Effort hydraulique ''''''''''
Property Get Fhyd() As Double
' Propriété en lecture
Fhyd = (Sc) * (Pc - Pg) - Sd * (Pd - Pg)

End Property
'''''''' Effort hydraulique ''''''''''
Property Get FhydDamp() As Double
' Propriété en lecture
FhydDamp = (Sc) * (mDeltaPc) - Sd * (-mDeltaPd)

End Property

'''''''' Effort Friction du joint ''''''''''
Property Get FFriJoi() As Double
' Propriété en lecture
If mv <> 0 Then
mCoeffAtte = 1 / Sqr(0.95 + 0.28 * Sqr(1 / (90 * Abs(mv))))
'FFriJoi = Sgn(mv) * (fc * mDt * Application.WorksheetFunction.Pi + fh * Pd * Application.WorksheetFunction.Pi / 4 * (mASeal * mASeal - mDt * mDt)) * mCoeffAtte
FFriJoi = Sgn(mv) * 100 * mCoeffAtte
End If

End Property
'''''''' Effort Friction du joint ''''''''''
Property Get FFriBag() As Double
' Propriété en lecture
If mv <> 0 Then
mCoeffAtte = 1 / Sqr(0.8 + 0.28 * Sqr(1 / (2 * Abs(mv))))
'FFriBag = Sgn(mv) * (0.1 * Abs(mXGt) + 0.07 * Abs(mXGb)) * mCoeffAtte
FFriBag = Sgn(mv) * (0.1 * Abs(mXGt) + 0.1 * Abs(mXGb)) * mCoeffAtte
End If

End Property

'''''''' Effort Gaz ''''''''''
Property Get FGas() As Double
' Propriété en lecture

FGas = St * Pg

End Property

'''''''' Acceleration de la tige ''''''''''
Property Get a() As Double
' Propriété en lecture
a = ma
End Property
Property Let a(a As Double)
' Propriété en écriture
ma = a
End Property

'''''''' Vitesse de la tige ''''''''''
Property Get v() As Double
' Propriété en lecture
v = mv
End Property
Property Let v(v As Double)
' Propriété en écriture
mv = v
End Property

'''''''' Déplacement de la tige ''''''''''
Property Get D() As Double
' Propriété en lecture
D = md
End Property
Property Let D(D As Double)
' Propriété en écriture
md = D
End Property

'''''''' Debit compression ''''''''''
Property Get Qc() As Double
' Propriété en lecture
Qc = mQc

End Property
Property Let Qc(Qc As Double)
' Propriété en écriture
mQc = Qc
End Property

'''''''' Debit détente ''''''''''
Property Get Qd() As Double
' Propriété en lecture
Qd = Sd * v

End Property

'''''''' Débit dans la BH ''''''''''
Property Get Qbh() As Double
' Propriété en lecture
Qbh = mQbh
End Property
Property Let Qbh(Qbh As Double)
' Propriété en écriture
mQbh = Qbh
End Property
'''''''' Débit dans le piston ''''''''''
Property Get Qp() As Double
' Propriété en lecture
Qp = mQp
End Property
Property Let Qp(Qp As Double)
' Propriété en écriture
mQp = Qp
End Property
'''''''' Débit dans la fuite''''''''''
Property Get Qpl() As Double
' Propriété en lecture
Qpl = mQpl
End Property
Property Let Qpl(Qpl As Double)
' Propriété en écriture
mQpl = Qpl
End Property

'''''''' Position des section de la Bh ''''''''''
Property Get TabPosBh() As Double()
' Propriété en lecture
TabPosBh = mTabPosBh
End Property
Property Let TabPosBh(ByRef TabPosBh() As Double)
' Propriété en écriture
mTabPosBh = TabPosBh
End Property
'''''''' Valeur des section de la Bh ''''''''''
Property Get TabSecBh() As Double()
' Propriété en lecture
TabSecBh = mTabSecBh
End Property
Property Let TabSecBh(ByRef TabSecBh() As Double)
' Propriété en écriture
mTabSecBh = TabSecBh
End Property

'''''''' Section de Bh ''''''''''
Property Get SecBh() As Double

'On recherche la position dans le tableau de Pos
Dim i As Integer
If md < mTabPosBh()(0) Then
SecBh = mTabSecBh()(0)
Else
For i = 0 To UBound(mTabPosBh()) - 1
 If md >= mTabPosBh()(i) And md < mTabPosBh()(i + 1) Then
 Exit For
 End If
Next
If i < UBound(mTabPosBh()) Then
SecBh = mTabSecBh()(i) + (md - mTabPosBh()(i)) * ((mTabSecBh()(i + 1) - mTabSecBh()(i)) / (mTabPosBh()(i + 1) - mTabPosBh()(i)))
Else
SecBh = mTabSecBh()(i)
End If
End If

End Property

'''''''' Section de Bh ''''''''''
Property Get SecBhDet() As Double

'On recherche la position dans le tableau de Pos
Dim i As Integer
If (md - mHauteurPisBh) < mTabPosBh()(0) Then
SecBhDet = mTabSecBh()(0) * 0 - mTabSecBh()(0) * 0 + mTabSecBh()(UBound(mTabPosBh()) - 3)
Else
For i = 0 To UBound(mTabPosBh()) - 1
 If (md - mHauteurPisBh) >= mTabPosBh()(i) And (md - mHauteurPisBh) < mTabPosBh()(i + 1) Then
 Exit For
 End If
Next
If i < UBound(mTabPosBh()) Then
SecBhDet = mTabSecBh()(UBound(mTabPosBh()) - 3) + mTabSecBh()(0) - (mTabSecBh()(i) + ((md - mHauteurPisBh) - mTabPosBh()(i)) * ((mTabSecBh()(i + 1) - mTabSecBh()(i)) / (mTabPosBh()(i + 1) - mTabPosBh()(i))))
Else
SecBhDet = mTabSecBh()(UBound(mTabPosBh()) - 3) + mTabSecBh()(0) - mTabSecBh()(i)
End If
End If

End Property

'''''''' Diamètre trou piston ''''''''''
Property Get DTrouPis() As Double
' Propriété en lecture
DTrouPis = mDTrouPis
End Property
Property Let DTrouPis(DTrouPis As Double)
' Propriété en écriture
mDTrouPis = DTrouPis
End Property

'''''''' Nombre trou piston ''''''''''
Property Get NbTrouPis() As Double
' Propriété en lecture
NbTrouPis = mNbTrouPis
End Property
Property Let NbTrouPis(NbTrouPis As Double)
' Propriété en écriture
mNbTrouPis = NbTrouPis
End Property

'''''''' Section trou piston ''''''''''
Property Get STrouPis() As Double
' Propriété en lecture
STrouPis = mNbTrouPis * mDTrouPis * mDTrouPis * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Diamètre longueur réalimentation du piston ''''''''''
Property Get LRealPis() As Double
' Propriété en lecture
LRealPis = mLRealPis
End Property
Property Let LRealPis(LRealPis As Double)
' Propriété en écriture
mLRealPis = LRealPis
End Property
'''''''' Diamètre hauteur réalimentation du piston ''''''''''
Property Get HRealPis() As Double
' Propriété en lecture
HRealPis = mHRealPis
End Property
Property Let HRealPis(HRealPis As Double)
' Propriété en écriture
mHRealPis = HRealPis
End Property
'''''''' Nombre réalimentation du piston ''''''''''
Property Get NbRealPis() As Double
' Propriété en lecture
NbRealPis = mNbRealPis
End Property
Property Let NbRealPis(NbRealPis As Double)
' Propriété en écriture
mNbRealPis = NbRealPis
End Property

'''''''' Section réalimentation du piston ''''''''''
Property Get SRealPis() As Double
' Propriété en lecture
SRealPis = mNbRealPis * mLRealPis * mHRealPis

End Property

'''''''' Diamètre trou Diap ''''''''''
Property Get DTrouDiap() As Double
' Propriété en lecture
DTrouDiap = mDTrouDiap
End Property
Property Let DTrouDiap(DTrouDiap As Double)
' Propriété en écriture
mDTrouDiap = DTrouDiap
End Property
'''''''' Nombre trou Diap ''''''''''
Property Get NbTrouDiap() As Double
' Propriété en lecture
NbTrouDiap = mNbTrouDiap
End Property
Property Let NbTrouDiap(NbTrouDiap As Double)
' Propriété en écriture
mNbTrouDiap = NbTrouDiap
End Property

'''''''' Section trou Diap ''''''''''
Property Get STrouDiap() As Double
' Propriété en lecture
STrouDiap = mNbTrouDiap * mDTrouDiap * mDTrouDiap * Application.WorksheetFunction.Pi / 4

End Property

'''''''' Diamètre fond de gorge de joint ''''''''''
Property Get ASeal() As Double
' Propriété en lecture
ASeal = mASeal
End Property
Property Let ASeal(ASeal As Double)
' Propriété en écriture
mASeal = ASeal
End Property
'''''''' Coefficient compression du joint ''''''''''
Property Get fc() As Double
' Propriété en lecture
fc = mfc
End Property
Property Let fc(fc As Double)
' Propriété en écriture
mfc = fc
End Property
'''''''' Coefficient effet de la pression ''''''''''
Property Get fh() As Double
' Propriété en lecture
fh = mfh
End Property
Property Let fh(fh As Double)
' Propriété en écriture
mfh = fh
End Property

'''''''' Effort guidage body ''''''''''
Property Get XGb() As Double
' Propriété en lecture
XGb = mXGb
End Property
Property Let XGb(XGb As Double)
' Propriété en écriture
mXGb = XGb
End Property
'''''''' Effort guidage tige ''''''''''
Property Get XGt() As Double
' Propriété en lecture
XGt = mXGt
End Property
Property Let XGt(XGt As Double)
' Propriété en écriture
mXGt = XGt
End Property
'''''''' Effort X total à la roue ''''''''''
Property Get XR() As Double
' Propriété en lecture
XR = mXR
End Property
Property Let XR(XR As Double)
' Propriété en écriture
mXR = XR
End Property

'''''''' Bulk de l'huile ''''''''''
Property Get OilBulk() As Double
' Propriété en lecture
OilBulk = mOilBulk
End Property
Property Let OilBulk(OilBulk As Double)
' Propriété en écriture
mOilBulk = OilBulk
End Property

'''''''' diamètre interieur de la BH ''''''''''
Property Get DInsideBh() As Double
' Propriété en lecture
DInsideBh = mDInsideBh
End Property
Property Let DInsideBh(DInsideBh As Double)
' Propriété en écriture
mDInsideBh = DInsideBh
End Property
'''''''' diamètre interieur de la tige ''''''''''
Property Get DIntTub() As Double
' Propriété en lecture
DIntTub = mDIntTub
End Property
Property Let DIntTub(DIntTub As Double)
' Propriété en écriture
mDIntTub = DIntTub
End Property
'''''''' diamètre metering valve''''''''''
Property Get DMetVal() As Double
' Propriété en lecture
DMetVal = mDMetVal
End Property
Property Let DMetVal(DMetVal As Double)
' Propriété en écriture
mDMetVal = DMetVal
End Property
'''''''' longueur metering valve''''''''''
Property Get LMetVal() As Double
' Propriété en lecture
LMetVal = mLMetVal
End Property
Property Let LMetVal(LMetVal As Double)
' Propriété en écriture
mLMetVal = LMetVal
End Property
'''''''' longueur metering valve''''''''''
Property Get cMetVal() As Double
' Propriété en lecture
cMetVal = (mDIntTub - mDMetVal) / 2

End Property
'''''''' Entraxe de l'amortisseur initial''''''''''
Property Get EntraxeInit() As Double
' Propriété en lecture
EntraxeInit = mEntraxeInit
End Property
Property Let EntraxeInit(EntraxeInit As Double)
' Propriété en écriture
mEntraxeInit = EntraxeInit
End Property
'''''''' Entraxe de l'amortisseur ''''''''''
Property Get Entraxe() As Double
' Propriété en lecture
Entraxe = mEntraxe
End Property
Property Let Entraxe(Entraxe As Double)
' Propriété en écriture
mEntraxe = Entraxe
End Property
'''''''' Longueur du trou de BH ''''''''''
Property Get Lbh() As Double
' Propriété en lecture
Lbh = mLbh
End Property
Property Let Lbh(Lbh As Double)
' Propriété en écriture
mLbh = Lbh
End Property
'''''''' Diamètre du trou intérieur de la BH ''''''''''
Property Get Dintbh() As Double
' Propriété en lecture
Dintbh = mDintbh
End Property
Property Let Dintbh(Dintbh As Double)
' Propriété en écriture
mDintbh = Dintbh
End Property

'''''''' Hauteur du piston de la BH ''''''''''
Property Get HauteurPisBh() As Double
' Propriété en lecture
HauteurPisBh = mHauteurPisBh
End Property
Property Let HauteurPisBh(HauteurPisBh As Double)
' Propriété en écriture
mHauteurPisBh = HauteurPisBh
End Property

'''''''' Gamma ''''''''''
Property Get Gamma() As Double
' Propriété en lecture
Gamma = mGamma
End Property
Property Let Gamma(Gamma As Double)
' Propriété en écriture
mGamma = Gamma
End Property
'''''''' Precision ''''''''''
Property Get Precision() As Double
' Propriété en lecture
Precision = mPrecision
End Property
Property Let Precision(Precision As Double)
' Propriété en écriture
mPrecision = Precision
End Property
