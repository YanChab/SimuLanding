Option Explicit
'avion
Dim PtG As New cPts
Dim PtOri As New cPts
Dim Pi As Double
Dim ChgtRep As New cRot
Dim NbIt As Double
Dim NbItCal As Double
Dim It As Double
Dim PMs As New cTorseur
Dim Ms As Double
Dim Lift As Double
Dim Vx As Double
Dim NbAffich As Integer
Dim j As Integer
Dim TempsSimu As Double
Dim Vitesse As Double
Dim CoeffAffich As Integer
Dim i As Long
Dim NbLigneBH As Integer
Dim NbLigneTyre As Integer
Dim NbLigneMu As Integer
Dim Attitude As Double
Dim JyyAvion As Double
Dim AccAvion As New cPts
Dim VitAvion As New cPts
Dim DepAvion As New cPts
Dim AccMnsNLG As New cPts
Dim VitMnsNLG As New cPts
Dim DepMnsNLG As New cPts
Dim AlpAvion As Double
Dim OmeAvion As Double
Dim TheAvion As Double
Dim ZGround As Double
Dim DeltaZAvion As Double
Dim DeltaThetaAvion As Double
Dim TbCal() As Double
Dim NombreNLG As Double
Dim NombreMLG As Double

'MLG
Dim MLG As New ClMLG
Dim Bal As New cBalancier
Dim H5606MLG As New ClOil
Dim PtBMLG As New cPts
Dim PtCMLG As New cPts
Dim PtAMLG As New cPts
Dim PtRMLG As New cPts
Dim PtSMLG As New cPts
Dim TBMLG_struc As New cTorseur 'Torseur en B des efforts sur la structure
Dim TBMLG_bal As New cTorseur 'Trorseur en B des efforts sur le balancier
Dim TRMLG As New cTorseur 'Torseur en R des efforts sur le balancier
Dim TAMLG As New cTorseur 'Torseurs en A des efforts sur le balancier
Dim TCMLG As New cTorseur 'Torseur en C des efforts sur la structure
Dim TyreMLG As New cTyre
Dim PMnsMLG As New cTorseur
Dim MnsMLG As Double

'NLG
Dim NLG As New ClNLG
Dim H5606NLG As New ClOil
Dim PtBNLG As New cPts
Dim PtGt As New cPts
Dim PtGb As New cPts
Dim PtCNLG As New cPts
Dim PtANLG As New cPts
Dim PtRNLG As New cPts
Dim TBNLG As New cTorseur 'Torseur en B des efforts sur la structure
Dim TRNLG As New cTorseur 'Torseur en R des efforts sur le train
Dim TANLG As New cTorseur 'Torseur en A des efforts sur le train
Dim TCNLG As New cTorseur ' Torseur en C des efforts sur la structure
Dim TGt As New cTorseur
Dim TGb As New cTorseur
Dim PtSNLG As New cPts
Dim TyreNLG As New cTyre
Dim PMnsNLG As New cTorseur
Dim MnsNLG As Double
Dim InclinaisonNLG As Double
Dim NLGEntraxe1 As Double
Dim NLGEntraxe2 As Double
Dim NLGEntraxe3 As Double
Dim NLGEntraxe4 As Double

Sub DropTestComplet()
Pi = Application.WorksheetFunction.Pi
Application.Calculation = xlCalculationManual 'Arrête certains calculs automatiques

'récupération des données
Call RecupData

'Initialisation
NbIt = Application.WorksheetFunction.RoundDown(TempsSimu / It, 0)
CoeffAffich = NbIt / 1000
NbAffich = 44
NbItCal = NbIt
ReDim TbCal(NbIt, NbAffich)
ReDim TbCalSum(NbIt, NbAffich)
AccAvion.RsolZ = 0
VitAvion.RsolZ = -Vitesse
DepAvion.RsolZ = 0
AlpAvion = 0
OmeAvion = 0
TheAvion = Attitude
MLG.v = 0
MLG.D = 0
NLG.v = 0
NLG.D = 0
TyreNLG.Accx = 0
TyreNLG.Vitx = 0
TyreNLG.Depx = 0
TyreMLG.Accx = 0
TyreMLG.Vitx = 0
TyreMLG.Depx = 0
'Stabilisation NLG
For i = 0 To 100000
    NLG.D = NLG.D - 0.00000001
    If Abs(NLG.Ftot) < 1 Then
    Exit For
    End If
Next
'On reposition les point R et Gb qui ont bouger suite à la stabilisation
PtRNLG.RlgZ = PtRNLG.RlgZ + NLG.D
PtGb.RlgZ = PtGb.RlgZ - NLG.D
'On Calcul les coordonnées dans les repères Sol
'lg vers SolNLG
ChgtRep.Pt_Rlg_RsolNLG PtRNLG
ChgtRep.Pt_Rlg_RsolNLG PtGb
'SolNLG vers Sol
PtRNLG.changementOrigineSolNLGSol PtG
PtGb.changementOrigineSolNLGSol PtG
NLGEntraxe1 = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
Call ChangementRepereNLGNouvellepositionRoue
NLGEntraxe2 = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
TyreNLG.Alpha = 0
TyreNLG.Omega = 0
TRNLG.RlgZ = 0
NLG.Entraxe = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)

'Stabilisation MLG
For i = 0 To 100000
    MLG.D = MLG.D - 0.00000001
    If Abs(MLG.Ftot) < 1 Then
    Exit For
    End If
Next
'détermination de la position des points R, S et A
MLG.Entraxe = MLG.EntraxeInit - MLG.D
Call DeterPosBalA
Call DeterPosBalR
Bal.ThRY = Atn((PtRMLG.RsolX - PtBMLG.RsolX) / (PtRMLG.RsolZ - PtBMLG.RsolZ))
Bal.ThAY = Atn((PtAMLG.RsolX - PtBMLG.RsolX) / (PtAMLG.RsolZ - PtBMLG.RsolZ))
TyreMLG.Alpha = 0
TyreMLG.Omega = 0
'Recalcul de la position du point S MLG et de la position du sol.
PtSMLG.RsolX = PtRMLG.RsolX
PtSMLG.RsolY = PtRMLG.RsolY
PtSMLG.RsolZ = PtRMLG.RsolZ - TyreMLG.UnRadius
ZGround = PtSMLG.RsolZ

'Test de  la boucle de calcul
'Itération de calcul

For i = 0 To NbIt
    'Affichage du temps de calcul
    TbCal(i, 0) = It * i:
    NLGEntraxe1 = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)

    'Calcul du déplacement des masse non suspendues
    'Pour le NLG
    AccMnsNLG.RlgZ = 1 / MnsNLG * (-NLG.Ftot + TRNLG.RlgZ)
    VitMnsNLG.RlgZ = VitMnsNLG.RlgZ + AccMnsNLG.RlgZ * It
    DepMnsNLG.RlgZ = DepMnsNLG.RlgZ + VitMnsNLG.RlgZ * It
    PtRNLG.RlgZ = PtRNLG.RlgZ + VitMnsNLG.RlgZ * It
    PtGb.RlgZ = PtGb.RlgZ + VitMnsNLG.RlgZ * It
    'Calcul des coordonnées dans le repère sol
    ChgtRep.Pt_Rlg_RsolNLG PtRNLG
    ChgtRep.Pt_Rlg_RsolNLG PtGb
    PtRNLG.changementOrigineSolNLGSol PtG
    PtGb.changementOrigineSolNLGSol PtG
    NLGEntraxe2 = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
    Call ChangementRepereNLGNouvellepositionRoue
    NLGEntraxe3 = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
    'Pour le MLG
    Bal.AlY = 1 / Bal.Jyy * ((PtAMLG.RsolZ - PtBMLG.RsolZ) * TAMLG.RsolX - (PtAMLG.RsolX - PtBMLG.RsolX) * TAMLG.RsolZ + (PtRMLG.RsolZ - PtBMLG.RsolZ) * TRMLG.RsolX - (PtRMLG.RsolX - PtBMLG.RsolX) * TRMLG.RsolZ)
    Bal.OmY = Bal.OmY + Bal.AlY * It
    Bal.ThAY = Bal.ThAY + Bal.OmY * It
    Bal.ThRY = Bal.ThRY + Bal.OmY * It
    PtRMLG.RsolX = -Bal.LgRB * Sin(Bal.ThRY) + PtBMLG.RsolX
    PtRMLG.RsolZ = -Bal.LgRB * Cos(Bal.ThRY) + PtBMLG.RsolZ
    PtAMLG.RsolX = -Bal.LgAB * Sin(Bal.ThAY) + PtBMLG.RsolX
    PtAMLG.RsolZ = -Bal.LgAB * Cos(Bal.ThAY) + PtBMLG.RsolZ
    'Calcul du PFD de l'avion
    AlpAvion = 1 / JyyAvion * ((PtRNLG.RsolZ - PtG.RsolZ) * TRNLG.RsolX * NombreNLG - (PtRNLG.RsolX - PtG.RsolX) * TRNLG.RsolZ * NombreNLG + (PtBMLG.RsolZ - PtG.RsolZ) * TBMLG_struc.RsolX * NombreMLG - (PtBMLG.RsolX - PtG.RsolX) * TBMLG_struc.RsolZ * NombreMLG + (PtCMLG.RsolZ - PtG.RsolZ) * TCMLG.RsolX * NombreMLG - (PtCMLG.RsolX - PtG.RsolX) * TCMLG.RsolZ * NombreMLG)
    'AlpAvion = 1 / JyyAvion * ((PtBNLG.RsolZ - PtG.RsolZ) * TBNLG.RsolX - (PtBNLG.RsolX - PtG.RsolX) * TBNLG.RsolZ + (PtCNLG.RsolZ - PtG.RsolZ) * TCNLG.RsolX - (PtCNLG.RsolX - PtG.RsolX) * TCNLG.RsolZ + (PtBMLG.RsolZ - PtG.RsolZ) * TBMLG_struc.RsolX - (PtBMLG.RsolX - PtG.RsolX) * TBMLG_struc.RsolZ + (PtCMLG.RsolZ - PtG.RsolZ) * TCMLG.RsolX - (PtCMLG.RsolX - PtG.RsolX) * TCMLG.RsolZ): TbCal(i, 12) = AlpAvion
    OmeAvion = OmeAvion + AlpAvion * It
    TheAvion = TheAvion + OmeAvion * It: TbCal(i, 3) = TheAvion * 360 / (2 * Pi)
    DeltaThetaAvion = OmeAvion * It
    'Rotation des point
    ChgtRep.RotSol PtG, DeltaThetaAvion
    ChgtRep.RotSol PtBNLG, DeltaThetaAvion
    ChgtRep.RotSol PtCNLG, DeltaThetaAvion
    ChgtRep.RotSol PtRNLG, DeltaThetaAvion
    ChgtRep.RotSol PtANLG, DeltaThetaAvion
    ChgtRep.RotSol PtGb, DeltaThetaAvion
    ChgtRep.RotSol PtGt, DeltaThetaAvion
    ChgtRep.RotSol PtBMLG, DeltaThetaAvion
    ChgtRep.RotSol PtCMLG, DeltaThetaAvion
    ChgtRep.RotSol PtRMLG, DeltaThetaAvion
    ChgtRep.RotSol PtAMLG, DeltaThetaAvion
    AccAvion.RsolZ = 1 / Ms * (TBMLG_struc.RsolZ * NombreMLG + TCMLG.RsolZ * NombreMLG + TRNLG.RsolZ * NombreNLG + PMs.RsolZ)
    'AccAvion.RsolZ = 1 / Ms * (TBMLG_struc.RsolZ + TCMLG.RsolZ + TBNLG.RsolZ + TCNLG.RsolZ + PMs.RsolZ)
    VitAvion.RsolZ = VitAvion.RsolZ + AccAvion.RsolZ * It: TbCal(i, 1) = VitAvion.RsolZ
    DepAvion.RsolZ = DepAvion.RsolZ + VitAvion.RsolZ * It: TbCal(i, 2) = DepAvion.RsolZ
    DeltaZAvion = VitAvion.RsolZ * It
    'Calcul de la nouvelle position des point
    'Le sol se rapproche
    ZGround = ZGround - DeltaZAvion: TbCal(i, 4) = ZGround
    'PtG.RsolZ = PtG.RsolZ + DeltaZAvion: TbCal(i, 5) = PtG.RsolZ
    'PtBNLG.RsolZ = PtBNLG.RsolZ + DeltaZAvion
    'PtCNLG.RsolZ = PtCNLG.RsolZ + DeltaZAvion
    'PtRNLG.RsolZ = PtRNLG.RsolZ + DeltaZAvion
    'PtANLG.RsolZ = PtANLG.RsolZ + DeltaZAvion
    'PtGb.RsolZ = PtGb.RsolZ + DeltaZAvion
    'PtGt.RsolZ = PtGt.RsolZ + DeltaZAvion
    'PtBMLG.RsolZ = PtBMLG.RsolZ + DeltaZAvion
    'PtCMLG.RsolZ = PtCMLG.RsolZ + DeltaZAvion
    'PtRMLG.RsolZ = PtRMLG.RsolZ + DeltaZAvion
    'PtAMLG.RsolZ = PtAMLG.RsolZ + DeltaZAvion
    'On recale le repère Sol pour garder G en origine

    PtRNLG.changementOrigineSolNLG PtRNLG
    PtBNLG.changementOrigineSolNLG PtRNLG
    PtANLG.changementOrigineSolNLG PtRNLG
    PtCNLG.changementOrigineSolNLG PtRNLG
    PtG.changementOrigineSolNLG PtRNLG
    PtGt.changementOrigineSolNLG PtRNLG
    PtGb.changementOrigineSolNLG PtRNLG

    'Calcul des coordonnées dans le repère lg NLG
    ChgtRep.alfap = Atn((PtBNLG.RsolNLGX - PtRNLG.RsolNLGX) / (PtBNLG.RsolNLGZ - PtRNLG.RsolNLGZ))
    InclinaisonNLG = ChgtRep.alfap * 360 / (2 * Pi): TbCal(i, 8) = InclinaisonNLG
    ChgtRep.Pt_RsolNLG_Rlg PtRNLG
    ChgtRep.Pt_RsolNLG_Rlg PtBNLG
    ChgtRep.Pt_RsolNLG_Rlg PtANLG
    ChgtRep.Pt_RsolNLG_Rlg PtCNLG
    ChgtRep.Pt_RsolNLG_Rlg PtGt
    ChgtRep.Pt_RsolNLG_Rlg PtGb

    'Calcul des efforts pneu MLG
    TyreMLG.Defl = TyreMLG.UnRadius - (PtRMLG.RsolZ - ZGround): TbCal(i, 15) = TyreMLG.Defl
    If Vx <> 0 Then
    TyreMLG.Slip = (Vx - TyreMLG.Omega * TyreMLG.REff) / Abs(Vx)
    Else
    TyreMLG.Slip = 0
    End If
    'calcul spin up
    TyreMLG.FSpin = TyreMLG.Mu * TRMLG.RsolZ * Sgn(TyreMLG.Slip)
    'Calcul springback
    TyreMLG.Accx = (-TyreMLG.Fx + TyreMLG.FSpin) / TyreMLG.WheelMass
    TyreMLG.Vitx = TyreMLG.Vitx + TyreMLG.Accx * It
    TyreMLG.Depx = TyreMLG.Depx + TyreMLG.Vitx * It

    TRMLG.RsolZ = TyreMLG.FTyre: TbCal(i, 17) = TRMLG.RsolZ
    TRMLG.RsolX = TyreMLG.Fx: TbCal(i, 16) = TRMLG.RsolX
    TyreMLG.Alpha = (TyreMLG.FSpin * (TyreMLG.UnRadius - TyreMLG.Defl)) / TyreMLG.j
    TyreMLG.Omega = TyreMLG.Omega + TyreMLG.Alpha * It
    'Calcul des efforts pneu NLG
    TyreNLG.Defl = TyreNLG.UnRadius - (PtRNLG.RsolZ - ZGround): TbCal(i, 5) = TyreNLG.Defl
    If Vx <> 0 Then
    TyreNLG.Slip = (Vx - TyreNLG.Omega * TyreNLG.REff) / Abs(Vx)
    Else
    TyreNLG.Slip = 0
    End If
    'calcul spin up
    TyreNLG.FSpin = TyreNLG.Mu * TRNLG.RsolZ * Sgn(TyreNLG.Slip)
    'Calcul springback
    TyreNLG.Accx = (-TyreNLG.Fx + TyreNLG.FSpin) / TyreNLG.WheelMass
    TyreNLG.Vitx = TyreNLG.Vitx + TyreNLG.Accx * It
    TyreNLG.Depx = TyreNLG.Depx + TyreNLG.Vitx * It

    TRNLG.RsolZ = TyreNLG.FTyre: TbCal(i, 7) = TRNLG.RsolZ
    TRNLG.RsolX = TyreNLG.Fx: TbCal(i, 6) = TRNLG.RsolX
    'Passage du torseur dans le repère lg NLG
    ChgtRep.Tor_Rsol_Rlg TRNLG
    TyreNLG.Alpha = (TyreNLG.FSpin * (TyreNLG.UnRadius - TyreNLG.Defl)) / TyreNLG.j
    TyreNLG.Omega = TyreNLG.Omega + TyreNLG.Alpha * It

    'Calcul de la vitesse NLG
    NLG.v = -(((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2) - NLG.Entraxe) / It: TbCal(i, 10) = NLG.v
    NLG.Entraxe = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
    NLG.D = NLG.EntraxeInit - NLG.Entraxe: TbCal(i, 9) = NLG.D
    'Calcul hydraulique NLG
    NLG.Pgtamp = NLG.Pg
    If NLG.v <> 0 Then
    Call CalculHydrauNLG:
    End If
    TbCal(i, 11) = NLG.Ftot: TbCal(i, 12) = NLG.Pg / 100000: TbCal(i, 13) = NLG.Pc / 100000: TbCal(i, 14) = NLG.Pd / 100000
    'Calcul de la vitesse MLG
    MLG.v = -(((PtCMLG.RsolX - PtAMLG.RsolX) ^ 2 + (PtCMLG.RsolY - PtAMLG.RsolY) ^ 2 + (PtCMLG.RsolZ - PtAMLG.RsolZ) ^ 2) ^ (1 / 2) - MLG.Entraxe) / It: TbCal(i, 19) = MLG.v
    MLG.Entraxe = ((PtCMLG.RsolX - PtAMLG.RsolX) ^ 2 + (PtCMLG.RsolY - PtAMLG.RsolY) ^ 2 + (PtCMLG.RsolZ - PtAMLG.RsolZ) ^ 2) ^ (1 / 2)
    MLG.D = MLG.EntraxeInit - MLG.Entraxe: TbCal(i, 18) = MLG.D
    'Calcul hydraulique MLG
    MLG.Pgtamp = MLG.Pg
    If MLG.v <> 0 Then
    Call CalculHydrauMLG:
    End If
     TbCal(i, 20) = MLG.Ftot: TbCal(i, 21) = MLG.Pg / 100000: TbCal(i, 22) = MLG.Pc / 100000: TbCal(i, 23) = MLG.Pd / 100000

    'Calcul des torseurs d'effort
    'MLG ATTENTION hypothèse AC dans le plan xz
    TAMLG.RsolZ = -MLG.Ftot * ((PtCMLG.RsolZ - PtAMLG.RsolZ) / MLG.Entraxe)
    TAMLG.RsolY = 0
    TAMLG.RsolX = -MLG.Ftot * ((PtCMLG.RsolX - PtAMLG.RsolX) / MLG.Entraxe)
    TCMLG.RsolZ = -TAMLG.RsolZ
    TCMLG.RsolY = -TAMLG.RsolY
    TCMLG.RsolX = -TAMLG.RsolX
    TBMLG_bal.RsolX = -TAMLG.RsolX - TRMLG.RsolX
    TBMLG_bal.RsolY = -TAMLG.RsolY - TRMLG.RsolY
    TBMLG_bal.RsolZ = -TAMLG.RsolZ - TRMLG.RsolZ
    TBMLG_struc.RsolX = -TBMLG_bal.RsolX
    TBMLG_struc.RsolY = -TBMLG_bal.RsolY
    TBMLG_struc.RsolZ = -TBMLG_bal.RsolZ

    'NLG
    NLG.XR = Sqr(TRNLG.RlgX ^ 2 + TRNLG.RlgY ^ 2)
    NLG.XGb = -(PtRNLG.RlgZ - PtGt.RlgZ) * NLG.XR / (PtGb.RlgZ - PtGt.RlgZ)
    NLG.XGt = -NLG.XGb - NLG.XR

    If i = 8134 Then
     i = i
    End If

Next

'Affichage
Call AffichageTest

Application.Calculation = xlAutomatic 'Réactive les calculs.

End Sub

Sub AffichageTest()

    Worksheets("Results Aircraft").Activate
    ActiveSheet.Cells.Select
    Selection.Clear
    Worksheets("Aircraft").Activate
    ActiveSheet.Cells(1, 1).Select

Sheets("Results Aircraft").Cells(2, 2) = "Temps (s)" '(0)
Sheets("Results Aircraft").Cells(2, 3) = "VitAvion.RsolZ" '(1)
Sheets("Results Aircraft").Cells(2, 4) = "DepAvion.RsolZ"
Sheets("Results Aircraft").Cells(2, 5) = "TheAvion"
Sheets("Results Aircraft").Cells(2, 6) = "ZGround"
Sheets("Results Aircraft").Cells(2, 7) = "TyreNLG.Defl" '(5)
Sheets("Results Aircraft").Cells(2, 8) = "TRNLG.RsolX"
Sheets("Results Aircraft").Cells(2, 9) = "TRNLG.RsolZ"
Sheets("Results Aircraft").Cells(2, 10) = "Inclinaison NLG"
Sheets("Results Aircraft").Cells(2, 11) = "NLG.d"
Sheets("Results Aircraft").Cells(2, 12) = "NLG.v" '(10)
Sheets("Results Aircraft").Cells(2, 13) = "NLG.Ftot"
Sheets("Results Aircraft").Cells(2, 14) = "NLG.Pg"
Sheets("Results Aircraft").Cells(2, 15) = "NLG.Pc"
Sheets("Results Aircraft").Cells(2, 16) = "NLG.Pd"
Sheets("Results Aircraft").Cells(2, 17) = "TyreMLG.Defl" '(15)
Sheets("Results Aircraft").Cells(2, 18) = "TRMLG.RsolX"
Sheets("Results Aircraft").Cells(2, 19) = "TRMLG.RsolZ"
Sheets("Results Aircraft").Cells(2, 20) = "MLG.d"
Sheets("Results Aircraft").Cells(2, 21) = "MLG.v"
Sheets("Results Aircraft").Cells(2, 22) = "MLG.Ftot" '(20)
Sheets("Results Aircraft").Cells(2, 23) = "MLG.Pg"
Sheets("Results Aircraft").Cells(2, 24) = "MLG.Pc"
Sheets("Results Aircraft").Cells(2, 25) = "MLG.Pd"
Sheets("Results Aircraft").Cells(2, 26) = ""
Sheets("Results Aircraft").Cells(2, 27) = ""
Sheets("Results Aircraft").Cells(2, 28) = ""
Sheets("Results Aircraft").Cells(2, 29) = ""
Sheets("Results Aircraft").Cells(2, 30) = ""
Sheets("Results Aircraft").Cells(2, 31) = ""
Sheets("Results Aircraft").Cells(2, 32) = ""
Sheets("Results Aircraft").Cells(2, 33) = ""
Sheets("Results Aircraft").Cells(2, 34) = ""
Sheets("Results Aircraft").Cells(2, 35) = ""
Sheets("Results Aircraft").Cells(2, 36) = ""
Sheets("Results Aircraft").Cells(2, 37) = ""
Sheets("Results Aircraft").Cells(2, 38) = ""
Sheets("Results Aircraft").Cells(2, 39) = ""
Sheets("Results Aircraft").Cells(2, 40) = ""
Sheets("Results Aircraft").Cells(2, 41) = ""
Sheets("Results Aircraft").Cells(2, 42) = ""
Sheets("Results Aircraft").Cells(2, 43) = ""
Sheets("Results Aircraft").Cells(2, 44) = ""
Sheets("Results Aircraft").Cells(2, 45) = ""

For i = 0 To Application.WorksheetFunction.RoundDown(NbItCal / CoeffAffich, 0)
    For j = 0 To NbAffich
        Sheets("Results Aircraft").Cells(3 + i, j + 2) = TbCal(i * CoeffAffich, j)
    Next
Next

End Sub

Sub RecupData()

'Avion
'On récupère les masse et torseur des poids
Lift = Sheets("Aircraft").Cells(13, 3)
Ms = Sheets("Aircraft").Cells(10, 3)
PMs.RsolZ = -Ms * 9.81 * (1 - Lift) 'conversion en N
Vx = Sheets("Aircraft").Cells(12, 3)
Vitesse = Sheets("Aircraft").Cells(11, 3)
TempsSimu = Sheets("Aircraft").Cells(15, 3)
It = Sheets("Aircraft").Cells(16, 3)
Attitude = Sheets("Aircraft").Cells(17, 3) * 2 * Pi / 360 'conversion en radians
JyyAvion = Sheets("Aircraft").Cells(19, 3)
PtG.RAirX = Sheets("Aircraft").Cells(25, 3) / 1000 ' conversion en m
PtG.RAirY = Sheets("Aircraft").Cells(25, 4) / 1000 ' conversion en m
PtG.RAirZ = Sheets("Aircraft").Cells(25, 5) / 1000 ' conversion en m
NombreNLG = Sheets("Aircraft").Cells(20, 3)
NombreMLG = Sheets("Aircraft").Cells(20, 3)

'MLG
Set MLG = Nothing
MLG.Dp = Sheets("MLG").Cells(35, 11) / 1000 ' conversion en m
MLG.Dbh = Sheets("MLG").Cells(36, 11) / 1000 ' conversion en m
MLG.Dt = Sheets("MLG").Cells(34, 11) / 1000 ' conversion en m
MLG.c = Sheets("MLG").Cells(39, 7) / 1000 ' conversion en m
MLG.Vh = Sheets("MLG").Cells(43, 7) / 1000000 'conversion en m3
MLG.Vgbp = Sheets("MLG").Cells(42, 7) / 1000000 'conversion en m3
MLG.Vginitbp = Sheets("MLG").Cells(42, 7) / 1000000 'conversion en m3
MLG.Pinitbp = Sheets("MLG").Cells(41, 7) * 100000 'conversion en Pa
MLG.Pgtamp = MLG.Pinitbp
MLG.Vghp = Sheets("MLG").Cells(45, 7) / 1000000 'conversion en m3
MLG.Vginithp = Sheets("MLG").Cells(45, 7) / 1000000 'conversion en m3
MLG.Pinithp = Sheets("MLG").Cells(44, 7) * 100000 'conversion en Pa
MLG.Gamma = Sheets("MLG").Cells(46, 7)

'trou de réalim du piston de détente
MLG.DTrouPis = Sheets("MLG").Cells(41, 11) / 1000 ' conversion en m
MLG.NbTrouPis = Sheets("MLG").Cells(42, 11)
MLG.DInsideBh = Sheets("MLG").Cells(37, 11) / 1000 ' conversion en m
MLG.Lbh = Sheets("MLG").Cells(38, 11) / 1000 ' conversion en m
MLG.HauteurPisBh = Sheets("MLG").Cells(43, 11) / 1000 ' conversion en m
MLG.DTrouDiap = Sheets("MLG").Cells(44, 11) / 1000 ' conversion en m
MLG.NbTrouDiap = Sheets("MLG").Cells(45, 11) ' conversion en m
MLG.Dpis = Sheets("MLG").Cells(46, 11) / 1000 ' conversion en m
MLG.OilBulk = Sheets("MLG").Cells(36, 15) * 1000000
MLG.Vtot = (Sheets("MLG").Cells(42, 7) + Sheets("MLG").Cells(43, 7) + Sheets("MLG").Cells(45, 7)) / 1000000 'conversion en m3
H5606MLG.Rho = Sheets("MLG").Cells(37, 15)
H5606MLG.Visc = Sheets("MLG").Cells(35, 15) / 1000000 'conversion en m²/s
H5606MLG.Bulk = Sheets("MLG").Cells(36, 15) * 1000000 'conversion en Pa
H5606MLG.Temp = Sheets("MLG").Cells(34, 15)

'On récupère les infos de la BH
NbLigneBH = Sheets("MLG").Cells(51, 10).End(xlDown).Row - 48 'on récupère le nombre de ligne du tableau de BH
Dim tPos() As Double 'vecteur tampon pour la position
Dim tSec() As Double 'vecteur tampon pour la section
ReDim tPos(NbLigneBH - 1)
ReDim tSec(NbLigneBH - 1)
For i = 0 To NbLigneBH - 1 'on bouble pour remplir les veteur tampon
tPos(i) = Sheets("MLG").Cells(51 + i, 10) / 1000 - Sheets("MLG").Cells(51 + i, 11) / 2000 'conversion en m
tSec(i) = Sheets("MLG").Cells(51 + i, 11) / 1000000 'conversion en m²
Next
MLG.TabPosBh() = tPos() 'on rempli les vecteurs du NLG
MLG.TabSecBh() = tSec()

'On récupères les infos du pneu
TyreMLG.UnRadius = Sheets("MLG").Cells(36, 3) / 1000 'conversion en m
NbLigneTyre = Sheets("MLG").Cells(40, 2).End(xlDown).Row - 39 + 2 'on récupère le nombre de ligne du tableau du pneu on rajoute une valeur en nég et une en +
Dim tDefl() As Double 'vecteur tampon pour la déflection
Dim tLoad() As Double 'vecteur tampon pour l'effort
ReDim tDefl(NbLigneTyre - 1)
ReDim tLoad(NbLigneTyre - 1)
tDefl(0) = -10
tLoad(0) = 0
For i = 1 To NbLigneTyre - 2 'on bouble pour remplir les veteur tampon
tDefl(i) = Sheets("MLG").Cells(39 + i, 2) / 1000 'conversion en m
tLoad(i) = Sheets("MLG").Cells(39 + i, 3) * 1000 'conversion en N
Next
tDefl(NbLigneTyre - 1) = tDefl(NbLigneTyre - 2) + 0.001 '1 mm de plus
tLoad(NbLigneTyre - 1) = tLoad(NbLigneTyre - 2) * 3 'on triple l'effort
TyreMLG.TabDefl() = tDefl()
TyreMLG.TabLoad() = tLoad()
'On récupère le muslip ratio
NbLigneMu = Sheets("MLG").Cells(64, 2).End(xlDown).Row - 63  'on récupère le nombre de ligne du tableau du muslip
Dim tMuX() As Double 'vecteur tampon pour la déflection
Dim tMuY() As Double 'vecteur tampon pour l'effort
ReDim tMuX(NbLigneMu - 1)
ReDim tMuY(NbLigneMu - 1)
For i = 0 To NbLigneMu - 1 'on bouble pour remplir les veteur tampon
tMuX(i) = Sheets("MLG").Cells(64 + i, 2)
tMuY(i) = Sheets("MLG").Cells(64 + i, 3)
Next
TyreMLG.MuSlipX() = tMuX()
TyreMLG.MuSlipY() = tMuY()
TyreMLG.j = Sheets("MLG").Cells(35, 7)
'Springback
TyreMLG.cx = Sheets("MLG").Cells(68, 7)
TyreMLG.kx = Sheets("MLG").Cells(67, 7)
TyreMLG.WheelMass = Sheets("MLG").Cells(69, 7)

'On récupère les coordonées des points
'On récupère les coordonées des points dans le repère appareil
PtBMLG.RAirX = Sheets("Aircraft").Cells(28, 3) / 1000 ' conversion en m
PtBMLG.RAirY = Sheets("Aircraft").Cells(28, 4) / 1000 ' conversion en m
PtBMLG.RAirZ = Sheets("Aircraft").Cells(28, 5) / 1000 ' conversion en m
PtAMLG.RAirX = Sheets("Aircraft").Cells(29, 3) / 1000 ' conversion en m
PtAMLG.RAirY = Sheets("Aircraft").Cells(29, 4) / 1000 ' conversion en m
PtAMLG.RAirZ = Sheets("Aircraft").Cells(29, 5) / 1000 ' conversion en m
PtCMLG.RAirX = Sheets("Aircraft").Cells(30, 3) / 1000 ' conversion en m
PtCMLG.RAirY = Sheets("Aircraft").Cells(30, 4) / 1000 ' conversion en m
PtCMLG.RAirZ = Sheets("Aircraft").Cells(30, 5) / 1000 ' conversion en m
PtRMLG.RAirX = Sheets("Aircraft").Cells(27, 3) / 1000 ' conversion en m
PtRMLG.RAirY = Sheets("Aircraft").Cells(27, 4) / 1000 ' conversion en m
PtRMLG.RAirZ = Sheets("Aircraft").Cells(27, 5) / 1000 ' conversion en m
PtSMLG.RAirX = PtRMLG.RAirX
PtSMLG.RAirY = PtRMLG.RAirY
PtSMLG.RAirZ = PtRMLG.RAirZ - TyreMLG.UnRadius

Set Bal = Nothing
MnsMLG = Sheets("MLG").Cells(34, 7)
PMnsMLG.RsolZ = MnsMLG * 9.81  'conversion en N
Bal.Jyy = Sheets("MLG").Cells(64, 7)

Set TBMLG_struc = Nothing
Set TBMLG_bal = Nothing
Set TRMLG = Nothing
Set TAMLG = Nothing
Set TCMLG = Nothing

'NLG
Set NLG = Nothing
NLG.Dp = Sheets("NLG").Cells(35, 11) / 1000 ' conversion en m
NLG.Dbh = Sheets("NLG").Cells(36, 11) / 1000 ' conversion en m
NLG.Dt = Sheets("NLG").Cells(34, 11) / 1000 ' conversion en m
NLG.c = Sheets("NLG").Cells(39, 7) / 1000 ' conversion en m
NLG.Vh = Sheets("NLG").Cells(43, 7) / 1000000 'conversion en m3
NLG.Vgbp = Sheets("NLG").Cells(42, 7) / 1000000 'conversion en m3
NLG.Vginitbp = Sheets("NLG").Cells(42, 7) / 1000000 'conversion en m3
NLG.Pinitbp = Sheets("NLG").Cells(41, 7) * 100000 'conversion en Pa
NLG.Pgtamp = NLG.Pinitbp
NLG.Vghp = Sheets("NLG").Cells(45, 7) / 1000000 'conversion en m3
NLG.Vginithp = Sheets("NLG").Cells(45, 7) / 1000000 'conversion en m3
NLG.Pinithp = Sheets("NLG").Cells(44, 7) * 100000 'conversion en Pa
NLG.Gamma = Sheets("NLG").Cells(46, 7)
'NLG.Pg = NLG.Pinit
'trou de réalim du piston de détente
NLG.DTrouPis = Sheets("NLG").Cells(41, 11) / 1000 ' conversion en m
NLG.NbTrouPis = Sheets("NLG").Cells(42, 11)
NLG.DInsideBh = Sheets("NLG").Cells(37, 11) / 1000 ' conversion en m
NLG.Lbh = Sheets("NLG").Cells(38, 11) / 1000 ' conversion en m
NLG.HauteurPisBh = Sheets("NLG").Cells(43, 11) / 1000 ' conversion en m
NLG.DTrouDiap = Sheets("NLG").Cells(44, 11) / 1000 ' conversion en m
NLG.NbTrouDiap = Sheets("NLG").Cells(45, 11) ' conversion en m
NLG.Dpis = Sheets("NLG").Cells(46, 11) / 1000 ' conversion en m
NLG.OilBulk = Sheets("NLG").Cells(36, 15) * 1000000
NLG.Vtot = (Sheets("NLG").Cells(42, 7) + Sheets("NLG").Cells(43, 7) + Sheets("NLG").Cells(45, 7)) / 1000000 'conversion en m3
NLG.BagueGuide = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
NLG.BaguePiston = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
NLG.fc = Sheets("NLG").Cells(43, 15) * 1000 ' conversion en N/m
NLG.ASeal = Sheets("NLG").Cells(42, 15) / 1000 ' conversion en N/m
NLG.BaguePiston = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
H5606NLG.Rho = Sheets("NLG").Cells(37, 15)
H5606NLG.Visc = Sheets("NLG").Cells(35, 15) / 1000000 'conversion en m²/s
H5606NLG.Bulk = Sheets("NLG").Cells(36, 15) * 1000000 'conversion en Pa
H5606NLG.Temp = Sheets("NLG").Cells(34, 15)

'On récupère les infos de la BH
NbLigneBH = Sheets("NLG").Cells(51, 10).End(xlDown).Row - 48 'on récupère le nombre de ligne du tableau de BH
'Dim tPos() As Double 'vecteur tampon pour la position
'Dim tSec() As Double 'vecteur tampon pour la section
ReDim tPos(NbLigneBH - 1)
ReDim tSec(NbLigneBH - 1)
For i = 0 To NbLigneBH - 1 'on bouble pour remplir les veteur tampon
tPos(i) = Sheets("NLG").Cells(51 + i, 10) / 1000 - Sheets("NLG").Cells(51 + i, 11) / 2000 'conversion en m
tSec(i) = Sheets("NLG").Cells(51 + i, 11) / 1000000 'conversion en m²
Next
NLG.TabPosBh() = tPos() 'on rempli les vecteurs du NLG
NLG.TabSecBh() = tSec()

'On récupères les infos du pneu
TyreNLG.UnRadius = Sheets("NLG").Cells(36, 3) / 1000 'conversion en m
NbLigneTyre = Sheets("NLG").Cells(40, 2).End(xlDown).Row - 39 + 2 'on récupère le nombre de ligne du tableau du pneu on rajoute une valeur en nég et une en +
'Dim tDefl() As Double 'vecteur tampon pour la déflection
'Dim tLoad() As Double 'vecteur tampon pour l'effort
ReDim tDefl(NbLigneTyre - 1)
ReDim tLoad(NbLigneTyre - 1)
tDefl(0) = -10
tLoad(0) = 0
For i = 1 To NbLigneTyre - 2 'on bouble pour remplir les veteur tampon
tDefl(i) = Sheets("NLG").Cells(39 + i, 2) / 1000 'conversion en m
tLoad(i) = Sheets("NLG").Cells(39 + i, 3) * 1000 'conversion en N
Next
tDefl(NbLigneTyre - 1) = tDefl(NbLigneTyre - 2) + 0.001 '1 mm de plus
tLoad(NbLigneTyre - 1) = tLoad(NbLigneTyre - 2) * 3 'on triple l'effort
TyreNLG.TabDefl() = tDefl()
TyreNLG.TabLoad() = tLoad()
'On récupère le muslip ratio
NbLigneMu = Sheets("NLG").Cells(64, 2).End(xlDown).Row - 63  'on récupère le nombre de ligne du tableau du muslip
'Dim tMuX() As Double 'vecteur tampon pour la déflection
'Dim tMuY() As Double 'vecteur tampon pour l'effort
ReDim tMuX(NbLigneMu - 1)
ReDim tMuY(NbLigneMu - 1)
For i = 0 To NbLigneMu - 1 'on bouble pour remplir les veteur tampon
tMuX(i) = Sheets("NLG").Cells(64 + i, 2)
tMuY(i) = Sheets("NLG").Cells(64 + i, 3)
Next
TyreNLG.MuSlipX() = tMuX()
TyreNLG.MuSlipY() = tMuY()
TyreNLG.j = Sheets("NLG").Cells(35, 7)
'Springback
TyreNLG.cx = Sheets("NLG").Cells(65, 7)
TyreNLG.kx = Sheets("NLG").Cells(64, 7)
TyreNLG.WheelMass = Sheets("NLG").Cells(66, 7)

'On récupère les coordonées des points
'On récupére les coordonnées dans le repère avion.
PtRNLG.RAirX = Sheets("Aircraft").Cells(32, 3) / 1000 ' conversion en m
PtRNLG.RAirY = Sheets("Aircraft").Cells(32, 4) / 1000 ' conversion en m
PtRNLG.RAirZ = Sheets("Aircraft").Cells(32, 5) / 1000 ' conversion en m
PtSNLG.RAirX = PtRNLG.RAirX
PtSNLG.RAirY = PtRNLG.RAirY
PtSNLG.RAirZ = PtRNLG.RAirZ - TyreNLG.UnRadius
PtBNLG.RAirX = Sheets("Aircraft").Cells(33, 3) / 1000 ' conversion en m
PtBNLG.RAirY = Sheets("Aircraft").Cells(33, 4) / 1000 ' conversion en m
PtBNLG.RAirZ = Sheets("Aircraft").Cells(33, 5) / 1000 ' conversion en m
PtGt.RAirX = Sheets("Aircraft").Cells(34, 3) / 1000 ' conversion en m
PtGt.RAirY = Sheets("Aircraft").Cells(34, 4) / 1000 ' conversion en m
PtGt.RAirZ = Sheets("Aircraft").Cells(34, 5) / 1000 ' conversion en m
PtGb.RAirX = Sheets("Aircraft").Cells(35, 3) / 1000 ' conversion en m
PtGb.RAirY = Sheets("Aircraft").Cells(35, 4) / 1000 ' conversion en m
PtGb.RAirZ = Sheets("Aircraft").Cells(35, 5) / 1000 ' conversion en m
PtANLG.RAirX = Sheets("Aircraft").Cells(36, 3) / 1000 ' conversion en m
PtANLG.RAirY = Sheets("Aircraft").Cells(36, 4) / 1000 ' conversion en m
PtANLG.RAirZ = Sheets("Aircraft").Cells(36, 5) / 1000 ' conversion en m
PtCNLG.RAirX = Sheets("Aircraft").Cells(37, 3) / 1000 ' conversion en m
PtCNLG.RAirY = Sheets("Aircraft").Cells(37, 4) / 1000 ' conversion en m
PtCNLG.RAirZ = Sheets("Aircraft").Cells(37, 5) / 1000 ' conversion en m

'On récupère les masse et torseur des poids
MnsNLG = Sheets("NLG").Cells(34, 7)
PMnsNLG.RsolZ = MnsNLG * 9.81  'conversion en N

Set TBNLG = Nothing
Set TRNLG = Nothing
Set TANLG = Nothing
Set TCNLG = Nothing
Set TGt = Nothing
Set TGb = Nothing

'Calculs des coordonées dans les repère sol
'Onrécupère les coordonées du repère aircraft dans le repère Sol en décalant l'origine au point G
PtG.changementOrigineSol PtG
PtRMLG.changementOrigineSol PtG
PtBMLG.changementOrigineSol PtG
PtAMLG.changementOrigineSol PtG
PtCMLG.changementOrigineSol PtG
PtRNLG.changementOrigineSol PtG
PtBNLG.changementOrigineSol PtG
PtANLG.changementOrigineSol PtG
PtCNLG.changementOrigineSol PtG
PtGt.changementOrigineSol PtG
PtGb.changementOrigineSol PtG
ChgtRep.RotSol PtG, Attitude
ChgtRep.RotSol PtRMLG, Attitude
ChgtRep.RotSol PtBMLG, Attitude
ChgtRep.RotSol PtAMLG, Attitude
ChgtRep.RotSol PtCMLG, Attitude
ChgtRep.RotSol PtRNLG, Attitude
ChgtRep.RotSol PtBNLG, Attitude
ChgtRep.RotSol PtANLG, Attitude
ChgtRep.RotSol PtCNLG, Attitude
ChgtRep.RotSol PtGt, Attitude
ChgtRep.RotSol PtGb, Attitude
'On fait le rotation lié à l'attitude initiales dans le repère sol
PtRMLG.changementOrigineSolMLG PtRMLG
PtBMLG.changementOrigineSolMLG PtRMLG
PtAMLG.changementOrigineSolMLG PtRMLG
PtCMLG.changementOrigineSolMLG PtRMLG
PtRNLG.changementOrigineSolNLG PtRNLG
PtBNLG.changementOrigineSolNLG PtRNLG
PtANLG.changementOrigineSolNLG PtRNLG
PtCNLG.changementOrigineSolNLG PtRNLG
PtG.changementOrigineSolNLG PtRNLG
PtGt.changementOrigineSolNLG PtRNLG
PtGb.changementOrigineSolNLG PtRNLG
'Calcul des points S
PtSMLG.RsolX = PtRMLG.RsolX
PtSMLG.RsolY = PtRMLG.RsolY
PtSMLG.RsolZ = PtRMLG.RsolZ - TyreMLG.UnRadius
PtSMLG.RsolMLGX = PtRMLG.RsolMLGX
PtSMLG.RsolMLGY = PtRMLG.RsolMLGY
PtSMLG.RsolMLGZ = PtRMLG.RsolMLGZ - TyreMLG.UnRadius
PtSNLG.RsolX = PtRNLG.RsolX
PtSNLG.RsolY = PtRNLG.RsolY
PtSNLG.RsolZ = PtRNLG.RsolZ - TyreNLG.UnRadius
PtSNLG.RsolNLGX = PtRNLG.RsolNLGX
PtSNLG.RsolNLGY = PtRNLG.RsolNLGY
PtSNLG.RsolNLGZ = PtRNLG.RsolNLGZ - TyreNLG.UnRadius
'On calul l'angle du NLG pour avoir ces coordonnées dans le repère landing gear
ChgtRep.alfap = Atn((PtBNLG.RsolNLGX - PtRNLG.RsolNLGX) / (PtBNLG.RsolNLGZ - PtRNLG.RsolNLGZ))
ChgtRep.Pt_RsolNLG_Rlg PtRNLG
ChgtRep.Pt_RsolNLG_Rlg PtBNLG
ChgtRep.Pt_RsolNLG_Rlg PtANLG
ChgtRep.Pt_RsolNLG_Rlg PtCNLG
ChgtRep.Pt_RsolNLG_Rlg PtGt
ChgtRep.Pt_RsolNLG_Rlg PtGb
ChgtRep.Pt_RsolNLG_Rlg PtSNLG

ZGround = PtSMLG.RsolZ

MLG.EntraxeInit = ((PtCMLG.RsolX - PtAMLG.RsolX) ^ 2 + (PtCMLG.RsolY - PtAMLG.RsolY) ^ 2 + (PtCMLG.RsolZ - PtAMLG.RsolZ) ^ 2) ^ (1 / 2)
NLG.EntraxeInit = ((PtBNLG.RlgX - PtRNLG.RlgX) ^ 2 + (PtBNLG.RlgY - PtRNLG.RlgY) ^ 2 + (PtBNLG.RlgZ - PtRNLG.RlgZ) ^ 2) ^ (1 / 2)
Bal.LgAB = ((PtBMLG.RsolX - PtAMLG.RsolX) ^ 2 + (PtBMLG.RsolY - PtAMLG.RsolY) ^ 2 + (PtBMLG.RsolZ - PtAMLG.RsolZ) ^ 2) ^ (1 / 2)
Bal.LgRB = ((PtBMLG.RsolX - PtRMLG.RsolX) ^ 2 + (PtBMLG.RsolZ - PtRMLG.RsolZ) ^ 2) ^ (1 / 2)
Bal.LgRA = ((PtAMLG.RsolX - PtRMLG.RsolX) ^ 2 + (PtAMLG.RsolZ - PtRMLG.RsolZ) ^ 2) ^ (1 / 2)
Bal.ThRY = -Atn((PtRMLG.RsolX - PtBMLG.RsolX) / (PtRMLG.RsolZ - PtBMLG.RsolZ))
Bal.ThAY = -Atn((PtAMLG.RsolX - PtBMLG.RsolX) / (PtAMLG.RsolZ - PtBMLG.RsolZ))

End Sub

Sub DeterPosBalA()

'On résoud le système pour calculer la perte de charge et les débits.
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: DeltaPc, 1: Qbh, 2: Qp
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim p As Double
Dim k As Double
Dim n As Double

xRes(0) = PtAMLG.RsolX
xRes(1) = PtAMLG.RsolZ

For p = 0 To 5
f(0) = MLG.Entraxe ^ 2 - (PtCMLG.RsolX - xRes(0)) ^ 2 - (PtCMLG.RsolZ - xRes(1)) ^ 2
f(1) = Bal.LgAB ^ 2 - (PtBMLG.RsolX - xRes(0)) ^ 2 - (PtBMLG.RsolZ - xRes(1)) ^ 2

df(0, 0) = 2 * PtCMLG.RsolX - 2 * xRes(0): df(0, 1) = 2 * PtCMLG.RsolZ - 2 * xRes(1)
df(1, 0) = 2 * PtBMLG.RsolX - 2 * xRes(0): df(1, 1) = 2 * PtBMLG.RsolZ - 2 * xRes(1)

'inversion de la matrice
det = Application.WorksheetFunction.MDeterm(df)

If det = 0 Then
    MsgBox ("le déterminant est nul")
    Else
    invdf = Application.WorksheetFunction.MInverse(df)
End If

'Calcul des inconnues:
    For k = 0 To neq
        For n = 0 To neq
            xRes(k) = xRes(k) - invdf(k + 1, n + 1) * f(n)
        Next
    Next

Next

PtAMLG.RsolX = xRes(0)
PtAMLG.RsolZ = xRes(1)

End Sub

Sub DeterPosBalR()

'On résoud le système pour calculer la perte de charge et les débits.
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: DeltaPc, 1: Qbh, 2: Qp
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim p As Double
Dim k As Double
Dim n As Double

xRes(0) = PtRMLG.RsolX
xRes(1) = PtRMLG.RsolZ

For p = 0 To 5
f(0) = Bal.LgRA ^ 2 - (PtAMLG.RsolX - xRes(0)) ^ 2 - (PtAMLG.RsolZ - xRes(1)) ^ 2
f(1) = Bal.LgRB ^ 2 - (PtBMLG.RsolX - xRes(0)) ^ 2 - (PtBMLG.RsolZ - xRes(1)) ^ 2

df(0, 0) = 2 * PtAMLG.RsolX - 2 * xRes(0): df(0, 1) = 2 * PtAMLG.RsolZ - 2 * xRes(1)
df(1, 0) = 2 * PtBMLG.RsolX - 2 * xRes(0): df(1, 1) = 2 * PtBMLG.RsolZ - 2 * xRes(1)

'inversion de la matrice
det = Application.WorksheetFunction.MDeterm(df)

If det = 0 Then
    MsgBox ("le déterminant est nul")
    Else
    invdf = Application.WorksheetFunction.MInverse(df)
End If

'Calcul des inconnues:
    For k = 0 To neq
        For n = 0 To neq
            xRes(k) = xRes(k) - invdf(k + 1, n + 1) * f(n)
        Next
    Next

Next

PtRMLG.RsolX = xRes(0)
PtRMLG.RsolZ = xRes(1)

End Sub

Sub ChangementRepereNLGNouvellepositionRoue()

'On recentre l'origine du repère solNLG sur le nouveau centre roue
PtRNLG.changementOrigineSolNLG PtRNLG
PtBNLG.changementOrigineSolNLG PtRNLG
PtANLG.changementOrigineSolNLG PtRNLG
PtCNLG.changementOrigineSolNLG PtRNLG
PtG.changementOrigineSolNLG PtRNLG
PtGt.changementOrigineSolNLG PtRNLG
PtGb.changementOrigineSolNLG PtRNLG
'On le rebalance dans le repère lg NLG
ChgtRep.alfap = Atn((PtBNLG.RsolNLGX - PtRNLG.RsolNLGX) / (PtBNLG.RsolNLGZ - PtRNLG.RsolNLGZ))
ChgtRep.Pt_RsolNLG_Rlg PtRNLG
ChgtRep.Pt_RsolNLG_Rlg PtBNLG
ChgtRep.Pt_RsolNLG_Rlg PtANLG
ChgtRep.Pt_RsolNLG_Rlg PtCNLG
ChgtRep.Pt_RsolNLG_Rlg PtGt
ChgtRep.Pt_RsolNLG_Rlg PtGb
ChgtRep.Pt_RsolNLG_Rlg PtSNLG

End Sub

Sub CalculHydrauNLG()
Dim DEqBh As Double
Dim ReBh As Double
Dim CdBh As Double
Dim DEqBhdet As Double
Dim ReBhdet As Double
Dim CdBhdet As Double
Dim RePis As Double
Dim CdPis As Double
Dim ReDiap As Double
Dim CdDiap As Double
'Calcul du Cd de la BH
'pour la compressibilité
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: PC, 1: Qc,
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim i As Integer
Dim k As Integer
Dim j As Integer

NLG.Qc = NLG.Sc * NLG.v

DEqBh = Sqr(Pi * NLG.SecBh / 4)
ReBh = (Abs(NLG.Qc) * DEqBh / (NLG.SecBh)) / H5606NLG.Visc

If ReBh * DEqBh / 0.003 < 50 Then
CdBh = (2.28 + 64 * 0.003 / (ReBh * DEqBh)) ^ (-1 / 2)
Else
CdBh = (1.5 + 13.74 * (0.003 / (ReBh * DEqBh)) ^ (1 / 2)) ^ (-1 / 2)
End If
DEqBhdet = Sqr(Pi * NLG.SecBh / 4)
ReBhdet = (Abs(NLG.Qc) * DEqBhdet / (NLG.SecBh)) / H5606NLG.Visc
If ReBhdet * DEqBhdet / 0.003 < 50 Then
    CdBhdet = (2.28 + 64 * 0.003 / (ReBhdet * DEqBhdet)) ^ (-1 / 2)
Else
    CdBhdet = (1.5 + 13.74 * (0.003 / (ReBhdet * DEqBhdet)) ^ (1 / 2)) ^ (-1 / 2)
End If

If NLG.Qc > 0 Then
    'NLG.DeltaPc = 1 / 2 * H5606.Rho * (NLG.Qc / (NLG.SecBh * CdBh)) ^ 2 * Sgn(NLG.Qc)
    'Test de l'intégration de la compressibilité de l'huile
    xRes(0) = NLG.Pc
    xRes(1) = NLG.Qc

    For i = 0 To 3
        f(0) = xRes(1) - NLG.Sc * NLG.v + NLG.Sc * (NLG.c - NLG.D) / H5606NLG.Bulk * (xRes(0) - NLG.Pc) / It
        f(1) = (xRes(0) - NLG.Pg) - 1 / 2 * H5606NLG.Rho * (xRes(1) / (NLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))
        'mPrecision  = f(0) + f(1)
        df(0, 0) = NLG.Sc * (NLG.c - NLG.D) / (H5606NLG.Bulk * It): df(0, 1) = 1
        df(1, 0) = 1: df(1, 1) = -xRes(1) * H5606NLG.Rho * (1 / (NLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))

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

        NLG.DeltaPc = xRes(0) - NLG.Pg
        NLG.Qc = xRes(1)
    Next

Else

   NLG.DeltaPc = 1 / 2 * H5606NLG.Rho * (NLG.Qc / (NLG.SecBh * CdBhdet)) ^ 2 * Sgn(NLG.Qc)
End If
'NLG.DeltaPbh = 128 * H5606.Rho * H5606.Visc * NLG.Lbh / (Pi * NLG.DInsideBh ^ 4) * NLG.Qc

RePis = (Abs(NLG.Qd) * NLG.DTrouPis / (NLG.STrouPis)) / H5606NLG.Visc
If RePis * NLG.DTrouPis / NLG.HauteurPisBh < 50 Then
CdPis = (2.28 + 64 * NLG.HauteurPisBh / (RePis * NLG.DTrouPis)) ^ (-1 / 2)
Else
CdPis = (1.5 + 13.74 * (NLG.HauteurPisBh / (RePis * NLG.DTrouPis)) ^ (1 / 2)) ^ (-1 / 2)
End If
ReDiap = (Abs(NLG.Qd) * NLG.DTrouDiap / (NLG.STrouDiap)) / H5606NLG.Visc
If ReDiap * NLG.DTrouDiap / 0.001 < 50 Then
CdDiap = (2.28 + 64 * 0.001 / (ReDiap * NLG.DTrouDiap)) ^ (-1 / 2)
Else
CdDiap = (1.5 + 13.74 * (0.001 / (ReDiap * NLG.DTrouDiap)) ^ (1 / 2)) ^ (-1 / 2)
End If

If NLG.Qd < 0 Then
    NLG.DeltaPd = 1 / 2 * H5606NLG.Rho * (NLG.Qd / (NLG.STrouDiap * CdDiap)) ^ 2 * Sgn(NLG.Qd) + 1 / 2 * H5606NLG.Rho * (NLG.Qd / (NLG.STrouPis * CdPis)) ^ 2 * Sgn(NLG.Qd)
Else
   NLG.DeltaPd = 1 / 2 * H5606NLG.Rho * (NLG.Qd / (NLG.STrouPis * CdPis)) ^ 2 * Sgn(NLG.Qd)
End If

End Sub

Sub CalculHydrauMLG()

Dim DEqBh As Double
Dim ReBh As Double
Dim CdBh As Double
Dim DEqBhdet As Double
Dim ReBhdet As Double
Dim CdBhdet As Double
Dim RePis As Double
Dim CdPis As Double
Dim ReDiap As Double
Dim CdDiap As Double
'pour la compressibilité
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: PC, 1: Qc,
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim i As Integer
Dim k As Integer
Dim j As Integer

'Calcul du Cd de la BH
MLG.Qc = MLG.Sc * MLG.v

DEqBh = Sqr(Pi * MLG.SecBh / 4)
ReBh = (Abs(MLG.Qc) * DEqBh / (MLG.SecBh)) / H5606MLG.Visc

If ReBh * DEqBh / 0.003 < 50 Then
CdBh = (2.28 + 64 * 0.003 / (ReBh * DEqBh)) ^ (-1 / 2)
Else
CdBh = (1.5 + 13.74 * (0.003 / (ReBh * DEqBh)) ^ (1 / 2)) ^ (-1 / 2)
End If

DEqBhdet = Sqr(Pi * MLG.SecBh / 4)
ReBhdet = (Abs(MLG.Qc) * DEqBhdet / (MLG.SecBh)) / H5606MLG.Visc
If ReBhdet * DEqBhdet / 0.003 < 50 Then
    CdBhdet = (2.28 + 64 * 0.003 / (ReBhdet * DEqBhdet)) ^ (-1 / 2)
Else
    CdBhdet = (1.5 + 13.74 * (0.003 / (ReBhdet * DEqBhdet)) ^ (1 / 2)) ^ (-1 / 2)
End If

If MLG.Qc > 0 Then
    'MLG.DeltaPc = 1 / 2 * H5606.Rho * (MLG.Qc / (MLG.SecBh * CdBh)) ^ 2 * Sgn(MLG.Qc)
    'Test de l'intégration de la compressibilité de l'huile
    xRes(0) = MLG.Pc
    xRes(1) = MLG.Qc

    For i = 0 To 3
        f(0) = xRes(1) - MLG.Sc * MLG.v + MLG.Sc * (MLG.c - MLG.D) / H5606MLG.Bulk * (xRes(0) - MLG.Pc) / It
        f(1) = (xRes(0) - MLG.Pg) - 1 / 2 * H5606MLG.Rho * (xRes(1) / (MLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))
        'mPrecision  = f(0) + f(1)
        df(0, 0) = MLG.Sc * (MLG.c - MLG.D) / (H5606MLG.Bulk * It): df(0, 1) = 1
        df(1, 0) = 1: df(1, 1) = -xRes(1) * H5606MLG.Rho * (1 / (MLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))

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

        MLG.DeltaPc = xRes(0) - MLG.Pg
        MLG.Qc = xRes(1)
    Next

Else

   MLG.DeltaPc = 1 / 2 * H5606MLG.Rho * (MLG.Qc / (MLG.SecBh * CdBhdet)) ^ 2 * Sgn(MLG.Qc)
End If
'MLG.DeltaPbh = 128 * H5606.Rho * H5606.Visc * MLG.Lbh / (Pi * MLG.DInsideBh ^ 4) * MLG.Qc

RePis = (Abs(MLG.Qd) * MLG.DTrouPis / (MLG.STrouPis)) / H5606MLG.Visc
If RePis * MLG.DTrouPis / MLG.HauteurPisBh < 50 Then
CdPis = (2.28 + 64 * MLG.HauteurPisBh / (RePis * MLG.DTrouPis)) ^ (-1 / 2)
Else
CdPis = (1.5 + 13.74 * (MLG.HauteurPisBh / (RePis * MLG.DTrouPis)) ^ (1 / 2)) ^ (-1 / 2)
End If
ReDiap = (Abs(MLG.Qd) * MLG.DTrouDiap / (MLG.STrouDiap)) / H5606MLG.Visc
If ReDiap * MLG.DTrouDiap / 0.001 < 50 Then
CdDiap = (2.28 + 64 * 0.001 / (ReDiap * MLG.DTrouDiap)) ^ (-1 / 2)
Else
CdDiap = (1.5 + 13.74 * (0.001 / (ReDiap * MLG.DTrouDiap)) ^ (1 / 2)) ^ (-1 / 2)
End If

If MLG.Qd < 0 Then
    MLG.DeltaPd = 1 / 2 * H5606MLG.Rho * (MLG.Qd / (MLG.STrouDiap * CdDiap)) ^ 2 * Sgn(MLG.Qd) + 1 / 2 * H5606MLG.Rho * (MLG.Qd / (MLG.STrouPis * CdPis)) ^ 2 * Sgn(MLG.Qd)
Else
   MLG.DeltaPd = 1 / 2 * H5606MLG.Rho * (MLG.Qd / (MLG.STrouPis * CdPis)) ^ 2 * Sgn(MLG.Qd)
End If

End Sub
