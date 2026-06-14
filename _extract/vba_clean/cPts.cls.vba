Option Explicit

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Coordonnées dans le repère Rsol                                   ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Private mPtDes As String
Private mRsolX As Double
Private mRsolY As Double
Private mRsolZ As Double
Private mRlgX As Double
Private mRlgY As Double
Private mRlgZ As Double
Private mRAirX As Double
Private mRAirY As Double
Private mRAirZ As Double
Private mRsolNLGX As Double
Private mRsolNLGY As Double
Private mRsolNLGZ As Double
Private mRsolMLGX As Double
Private mRsolMLGY As Double
Private mRsolMLGZ As Double
'repère avion : les coordonées de la 3D
'Repère sol : Origine au CDG
'Repère landing gear : origine centre roue et axe z = axe de coulisse
'Repère solMLG : centre roue MLG
'Repère solNLG : centre roue NLG

Property Get PtDes() As String
' Propriété en lecture
PtDes = mPtDes
End Property
Property Let PtDes(PtDes As String)
' Propriété en écriture
mPtDes = PtDes
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

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Coordonnées dans le repère  Rlg                                   ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

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

''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''           Coordonnées dans le repère  RAir avion comme le repère Sol mais avec comme origine le centre roue                                   ''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
Property Get RAirX() As Double
' Propriété en lecture
RAirX = mRAirX
End Property
Property Let RAirX(RAirX As Double)
' Propriété en écriture
mRAirX = RAirX
End Property

Property Get RAirY() As Double
' Propriété en lecture
RAirY = mRAirY
End Property
Property Let RAirY(RAirY As Double)
' Propriété en écriture
mRAirY = RAirY
End Property

Property Get RAirZ() As Double
' Propriété en lecture
RAirZ = mRAirZ
End Property
Property Let RAirZ(RAirZ As Double)
' Propriété en écriture
mRAirZ = RAirZ
End Property

'Repère Sol NLG
Property Get RsolNLGX() As Double
' Propriété en lecture
RsolNLGX = mRsolNLGX
End Property
Property Let RsolNLGX(RsolNLGX As Double)
' Propriété en écriture
mRsolNLGX = RsolNLGX
End Property
Property Get RsolNLGY() As Double
' Propriété en lecture
RsolNLGY = mRsolNLGY
End Property
Property Let RsolNLGY(RsolNLGY As Double)
' Propriété en écriture
mRsolNLGY = RsolNLGY
End Property
Property Get RsolNLGZ() As Double
' Propriété en lecture
RsolNLGZ = mRsolNLGZ
End Property
Property Let RsolNLGZ(RsolNLGZ As Double)
' Propriété en écriture
mRsolNLGZ = RsolNLGZ
End Property

'Repère Sol MLG
Property Get RsolMLGX() As Double
' Propriété en lecture
RsolMLGX = mRsolMLGX
End Property
Property Let RsolMLGX(RsolMLGX As Double)
' Propriété en écriture
mRsolMLGX = RsolMLGX
End Property
Property Get RsolMLGY() As Double
' Propriété en lecture
RsolMLGY = mRsolMLGY
End Property
Property Let RsolMLGY(RsolMLGY As Double)
' Propriété en écriture
mRsolMLGY = RsolMLGY
End Property
Property Get RsolMLGZ() As Double
' Propriété en lecture
RsolMLGZ = mRsolMLGZ
End Property
Property Let RsolMLGZ(RsolMLGZ As Double)
' Propriété en écriture
mRsolMLGZ = RsolMLGZ
End Property

Public Sub recupCoord(mRep As String, mCell As Object)

    Dim mlig As Integer 'numéro de ligne
    Dim mcol As Integer 'numéro de colonne
    mCell.Select 'on séléection la cellule nCell ATTENTION si l'onglet Data n'est pas sélectionné ça bug
    mlig = ActiveCell.Row 'on récupère la ligne
    mcol = ActiveCell.Column 'on récupère la colonne
    mPtDes = Cells(mlig, mcol) 'On récupère le nom du point

'On récupère les coordonnées correspondant au bon repère
    Select Case mRep
        Case "Rsol"
        mRsolX = Cells(mlig, mcol + 1)
        mRsolY = Cells(mlig, mcol + 2)
        mRsolZ = Cells(mlig, mcol + 3)
        Case "Rlg"
        mRlgX = Cells(mlig, mcol + 1)
        mRlgY = Cells(mlig, mcol + 2)
        mRlgZ = Cells(mlig, mcol + 3)
    End Select
End Sub

Public Sub changementOrigineAircraft(mOri As cPts)

    mRAirX = mRsolX - mOri.RsolX
    mRAirY = mRsolY - mOri.RsolY
    mRAirZ = mRsolZ - mOri.RsolZ

End Sub

Public Sub changementOrigineSol(mOri As cPts)

    mRsolX = mRAirX - mOri.RAirX
    mRsolY = mRAirY - mOri.RAirY
    mRsolZ = mRAirZ - mOri.RAirZ

End Sub
Public Sub changementOrigineSolNLG(mOri As cPts)

    mRsolNLGX = mRsolX - mOri.RsolX
    mRsolNLGY = mRsolY - mOri.RsolY
    mRsolNLGZ = mRsolZ - mOri.RsolZ

End Sub
Public Sub changementOrigineSolMLG(mOri As cPts)

    mRsolMLGX = mRsolX - mOri.RsolX
    mRsolMLGY = mRsolY - mOri.RsolY
    mRsolMLGZ = mRsolZ - mOri.RsolZ

End Sub

Public Sub changementOrigineSolNLGSol(mOri As cPts)

    mRsolX = mRsolNLGX - mOri.RsolNLGX
    mRsolY = mRsolNLGY - mOri.RsolNLGY
    mRsolZ = mRsolNLGZ - mOri.RsolNLGZ

End Sub
