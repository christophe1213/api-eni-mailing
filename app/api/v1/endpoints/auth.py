from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import Utilisateur
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    LoginPayload,
    Token,
    ChangePasswordPayload,
    ForgotPasswordPayload,
)
from app.schemas.user import UserResponse, RegisterPayload, UserUpdate
from app.schemas.otp import (
    VerifyOtpPayload,
    ResendOtpPayload,
    VerifyResetOtpPayload,
    ResetPasswordPayload,
    OtpResponse,
    VerifyResetOtpResponse,
)
from app.services.auth_service import auth_service
from app.services.user_service import user_service, user_to_response
from app.services.audit_service import audit_service
from app.services.otp_service import otp_service
from app.services.avatar_service import avatar_service
from app.services.email_service import email_service
from app.core.security import verify_password, get_password_hash

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    login_data: LoginPayload,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    auth_result = auth_service.authenticate(db, login_data=login_data)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse e-mail ou mot de passe incorrect.",
        )
    token, user = auth_result
    # Journaliser la connexion
    client_ip = request.client.host if request.client else None
    audit_service.log(db, user_id=user.id, action="LOGIN", details="Connexion réussie", ip=client_ip)
    return {"token": token, "user": user}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
) -> Any:
    existing_user = user_service.get_by_email(db, email=payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un utilisateur avec cet email existe déjà.",
        )
    existing_mat = user_service.get_by_matricule(db, matricule=payload.matricule)
    if existing_mat:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un utilisateur avec ce matricule existe déjà.",
        )
    existing_verif = user_repository.get_by_email_verification(
        db, email=payload.email_verification
    )
    if existing_verif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse e-mail de vérification est déjà utilisée.",
        )

    # 1. Création de l'utilisateur avec is_verified=False
    new_user = auth_service.register(db, payload=payload)
    client_ip = request.client.host if request.client else None

    # 2. Génération du code OTP de vérification d'e-mail
    otp_code = otp_service.create_otp(db, user_id=new_user.id, purpose="REGISTER")

    # 3. Envoi sécurisé par e-mail
    background_tasks.add_task(
        email_service.send_otp_email,
        recipient_email=new_user.email_verification,
        recipient_name=f"{new_user.prenom} {new_user.nom}",
        code=otp_code,
        purpose="REGISTER",
    )

    audit_service.log(
        db,
        user_id=new_user.id,
        action="REGISTER",
        details={"email": new_user.email, "role": new_user.role},
        ip=client_ip,
    )

    return {
        "email": payload.email,
        "pending": True,
        "is_verified": False,
        "message": "Inscription enregistrée. Un code OTP de validation a été envoyé à votre adresse e-mail.",
    }


@router.post("/verify-otp", response_model=OtpResponse)
def verify_otp(
    payload: VerifyOtpPayload,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = user_repository.get_by_email(db, email=payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun compte associé à cette adresse e-mail.",
        )

    # Si déjà vérifié pour l'inscription
    if payload.purpose == "REGISTER" and getattr(user, "is_verified", False):
        return {
            "success": True,
            "message": "Votre adresse e-mail est déjà vérifiée. Votre compte est en attente de validation administrative.",
        }

    # Validation du code OTP
    otp_service.verify_otp(
        db, user_id=user.id, code=payload.code, purpose=payload.purpose
    )

    if payload.purpose == "REGISTER":
        user.is_verified = True
        user.email_verification_verifie = True
        db.add(user)
        db.commit()

    client_ip = request.client.host if request.client else None
    audit_service.log(
        db,
        user_id=user.id,
        action="OTP_VERIFIED",
        details={"email": user.email, "purpose": payload.purpose},
        ip=client_ip,
    )

    return {
        "success": True,
        "message": "Adresse e-mail vérifiée avec succès. Votre compte est prêt.",
    }


@router.post("/resend-otp", response_model=OtpResponse)
def resend_otp(
    payload: ResendOtpPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = user_repository.get_by_email(db, email=payload.email)
    # Message générique pour éviter l'énumération des utilisateurs
    if not user:
        return {
            "success": True,
            "message": "Si l'adresse e-mail est valide, un nouveau code vous a été envoyé.",
        }

    if payload.purpose == "REGISTER" and getattr(user, "is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse e-mail est déjà vérifiée.",
        )

    if not user.email_verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune adresse e-mail de vérification n'est associée à ce compte.",
        )
    if payload.purpose == "PASSWORD_RESET" and not user.email_verification_verifie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'adresse e-mail de vérification n'a pas encore été validée.",
        )

    # create_otp lève automatiquement 429 si dans les 60s
    code = otp_service.create_otp(db, user_id=user.id, purpose=payload.purpose)

    background_tasks.add_task(
        email_service.send_otp_email,
        recipient_email=user.email_verification,
        recipient_name=f"{user.prenom} {user.nom}",
        code=code,
        purpose=payload.purpose,
    )

    client_ip = request.client.host if request.client else None
    audit_service.log(
        db,
        user_id=user.id,
        action="OTP_RESENT",
        details={"email": user.email, "purpose": payload.purpose},
        ip=client_ip,
    )

    return {
        "success": True,
        "message": "Un nouveau code de vérification vous a été envoyé par e-mail.",
    }


@router.post("/forgot-password", response_model=OtpResponse)
def forgot_password(
    payload: ForgotPasswordPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = user_repository.get_by_email(db, email=payload.email)
    client_ip = request.client.host if request.client else None

    # Réponse générique quel que soit le cas pour éviter l'énumération des comptes
    generic_response = {
        "success": True,
        "message": "Si un compte est associé à cette adresse e-mail, un code de réinitialisation vous a été envoyé.",
    }

    if not user or not user.actif:
        return generic_response

    # Le code de réinitialisation n'est envoyé qu'à l'e-mail externe déjà vérifié
    if not user.email_verification or not user.email_verification_verifie:
        return generic_response

    # Générer le code OTP de réinitialisation (en tenant compte du cooldown de 60s)
    try:
        code = otp_service.create_otp(db, user_id=user.id, purpose="PASSWORD_RESET")
        background_tasks.add_task(
            email_service.send_otp_email,
            recipient_email=user.email_verification,
            recipient_name=f"{user.prenom} {user.nom}",
            code=code,
            purpose="PASSWORD_RESET",
        )
        audit_service.log(
            db,
            user_id=user.id,
            action="FORGOT_PASSWORD_REQUEST",
            details={"email": user.email},
            ip=client_ip,
        )
    except HTTPException as e:
        # Si cooldown actif, on propage l'erreur 429 pour informer l'utilisateur
        if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise e

    return generic_response


@router.post("/verify-reset-otp", response_model=VerifyResetOtpResponse)
def verify_reset_otp(
    payload: VerifyResetOtpPayload,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = user_repository.get_by_email(db, email=payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification invalide ou expiré.",
        )

    # Vérification du code OTP de type PASSWORD_RESET
    otp_service.verify_otp(
        db, user_id=user.id, code=payload.code, purpose="PASSWORD_RESET"
    )

    # Générer le jeton sécurisé temporaire pour réinitialiser le mot de passe
    reset_token = otp_service.create_reset_token(user_id=user.id, email=user.email)

    return {
        "success": True,
        "reset_token": reset_token,
        "message": "Code vérifié. Vous pouvez maintenant choisir votre nouveau mot de passe.",
    }


@router.post("/reset-password", response_model=OtpResponse)
def reset_password(
    payload: ResetPasswordPayload,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    user_id = otp_service.verify_reset_token(
        token=payload.reset_token, email=payload.email
    )
    user = user_repository.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé.",
        )

    # Mise à jour sécurisée du mot de passe
    user.mot_de_passe = get_password_hash(payload.new_password)
    user.is_verified = True  # Valide l'adresse e-mail si ce n'était pas déjà fait
    db.add(user)
    db.commit()

    client_ip = request.client.host if request.client else None
    audit_service.log(
        db,
        user_id=user.id,
        action="PASSWORD_RESET_SUCCESS",
        details={"email": user.email},
        ip=client_ip,
    )

    return {
        "success": True,
        "message": "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.",
    }


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    return user_service.update_profile(db, user=current_user, payload=payload)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    user = await avatar_service.save(db, user=current_user, file=file)
    return user_to_response(user)


@router.delete("/me/avatar", response_model=UserResponse)
def delete_avatar(
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> Any:
    user = avatar_service.delete(db, user=current_user)
    return user_to_response(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordPayload,
    db: Session = Depends(deps.get_db),
    current_user: Utilisateur = Depends(deps.get_current_active_user),
) -> None:
    if not verify_password(payload.current_password, current_user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe actuel est incorrect.",
        )
    current_user.mot_de_passe = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return None
