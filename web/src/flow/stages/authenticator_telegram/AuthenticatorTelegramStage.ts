import "#flow/FormStatic";
import "#flow/components/ak-flow-card";

import { SlottedTemplateResult } from "#elements/types";

import { AKFormErrors } from "#components/ak-field-errors";
import { AKLabel } from "#components/ak-label";

import { FlowUserDetails } from "#flow/FormStatic";
import { loadTelegramWidget, TelegramUserResponse } from "#flow/sources/telegram/utils";
import { BaseStage } from "#flow/stages/base";

import {
    AuthenticatorTelegramChallenge,
    AuthenticatorTelegramChallengeResponseRequest,
} from "@goauthentik/api";

import { msg } from "@lit/localize";
import { CSSResult, html, nothing, PropertyValues } from "lit";
import { customElement } from "lit/decorators.js";
import { createRef, ref } from "lit/directives/ref.js";

import PFAlert from "@patternfly/patternfly/components/Alert/alert.css";
import PFButton from "@patternfly/patternfly/components/Button/button.css";
import PFForm from "@patternfly/patternfly/components/Form/form.css";
import PFFormControl from "@patternfly/patternfly/components/FormControl/form-control.css";
import PFInputGroup from "@patternfly/patternfly/components/InputGroup/input-group.css";
import PFLogin from "@patternfly/patternfly/components/Login/login.css";
import PFTitle from "@patternfly/patternfly/components/Title/title.css";

@customElement("ak-stage-authenticator-telegram")
export class AuthenticatorTelegramStage extends BaseStage<
    AuthenticatorTelegramChallenge,
    AuthenticatorTelegramChallengeResponseRequest
> {
    static styles: CSSResult[] = [
        PFAlert,
        PFLogin,
        PFForm,
        PFFormControl,
        PFInputGroup,
        PFTitle,
        PFButton,
    ];

    widgetTargetRef = createRef();
    widgetLoaded = false;

    public override updated(changedProperties: PropertyValues<this>) {
        super.updated(changedProperties);
        if (!changedProperties.has("challenge") || !this.challenge) {
            return;
        }
        if (this.challenge.codeRequired || this.widgetLoaded) {
            return;
        }

        this.widgetLoaded = true;
        loadTelegramWidget(
            this.widgetTargetRef.value,
            this.challenge.botUsername,
            true,
            (user: TelegramUserResponse) => {
                this.host.submit({
                    id: user.id,
                    authDate: user.auth_date,
                    hash: user.hash,
                    firstName: user.first_name,
                    lastName: user.last_name,
                    username: user.username,
                    photoUrl: user.photo_url,
                });
            },
        );
    }

    protected renderCode(): SlottedTemplateResult {
        if (!this.challenge) {
            return nothing;
        }

        return html`<ak-flow-card .challenge=${this.challenge}>
            <form class="pf-c-form" @submit=${this.submitForm}>
                ${FlowUserDetails({ challenge: this.challenge })}
                <div class="pf-c-form__group">
                    ${AKLabel({ required: true, htmlFor: "telegram-code-input" }, msg("Code"))}
                    <input
                        id="telegram-code-input"
                        type="text"
                        name="code"
                        inputmode="numeric"
                        pattern="[0-9]*"
                        placeholder="${msg("Please enter the code you received via Telegram")}"
                        autofocus
                        autocomplete="one-time-code"
                        class="pf-c-form-control pf-m-monospace"
                        required
                    />
                    ${AKFormErrors({ errors: this.challenge.responseErrors?.code })}
                </div>
                ${this.renderNonFieldErrors()}
                <fieldset class="ak-c-fieldset pf-c-form__group pf-m-action">
                    <legend class="sr-only">${msg("Form actions")}</legend>
                    <button
                        name="continue"
                        type="submit"
                        class="pf-c-button pf-m-primary pf-m-block"
                    >
                        ${msg("Continue")}
                    </button>
                </fieldset>
            </form>
        </ak-flow-card>`;
    }

    protected renderWidget(): SlottedTemplateResult {
        if (!this.challenge) {
            return nothing;
        }

        return html`
            <form class="pf-c-form">
                <ak-flow-card .challenge=${this.challenge}>
                    ${FlowUserDetails({ challenge: this.challenge })}
                    <p>${msg("Click the button below to link your Telegram account.")}</p>
                    <div ${ref(this.widgetTargetRef)}></div>
                    ${this.renderNonFieldErrors()}
                </ak-flow-card>
            </form>
        `;
    }

    render(): SlottedTemplateResult {
        if (this.challenge?.codeRequired) {
            return this.renderCode();
        }

        return this.renderWidget();
    }
}

export default AuthenticatorTelegramStage;

declare global {
    interface HTMLElementTagNameMap {
        "ak-stage-authenticator-telegram": AuthenticatorTelegramStage;
    }
}
