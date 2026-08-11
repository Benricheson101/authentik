import "#elements/forms/FormGroup";
import "#elements/forms/HorizontalFormElement";
import "#elements/forms/SearchSelect/index";
import "#components/ak-secret-text-input";

import { aki } from "#common/api/client";

import { RenderFlowOption } from "#admin/flows/utils";
import { BaseStageForm } from "#admin/stages/BaseStageForm";

import {
    AuthenticatorTelegramStage,
    AuthenticatorTelegramStageRequest,
    Flow,
    FlowDesignationEnum,
    FlowsApi,
    FlowsInstancesListRequest,
    NotificationWebhookMapping,
    PropertymappingsApi,
    PropertymappingsNotificationListRequest,
    StagesApi,
} from "@goauthentik/api";

import { msg } from "@lit/localize";
import { html, TemplateResult } from "lit";
import { customElement } from "lit/decorators.js";

@customElement("ak-stage-authenticator-telegram-form")
export class AuthenticatorTelegramStageForm extends BaseStageForm<AuthenticatorTelegramStage> {
    loadInstance(pk: string): Promise<AuthenticatorTelegramStage> {
        return aki(StagesApi).stagesAuthenticatorTelegramRetrieve({
            stageUuid: pk,
        });
    }

    async send(data: AuthenticatorTelegramStage): Promise<AuthenticatorTelegramStage> {
        if (this.instance) {
            return aki(StagesApi).stagesAuthenticatorTelegramUpdate({
                stageUuid: this.instance.pk || "",
                authenticatorTelegramStageRequest:
                    data as unknown as AuthenticatorTelegramStageRequest,
            });
        }
        return aki(StagesApi).stagesAuthenticatorTelegramCreate({
            authenticatorTelegramStageRequest: data as unknown as AuthenticatorTelegramStageRequest,
        });
    }

    protected override renderForm(): TemplateResult {
        return html` <span>
                ${msg("Stage used to configure a Telegram-based TOTP authenticator.")}
            </span>
            <ak-form-element-horizontal label=${msg("Name")} required name="name">
                <input
                    type="text"
                    value="${this.instance?.name ?? ""}"
                    class="pf-c-form-control"
                    required
                />
            </ak-form-element-horizontal>
            <ak-form-element-horizontal
                label=${msg("Authenticator type name")}
                ?required=${false}
                name="friendlyName"
            >
                <input
                    type="text"
                    value="${this.instance?.friendlyName ?? ""}"
                    class="pf-c-form-control"
                />
                <p class="pf-c-form__helper-text">
                    ${msg(
                        "Display name of this authenticator, used by users when they enroll an authenticator.",
                    )}
                </p>
            </ak-form-element-horizontal>
            <ak-form-group open label="${msg("Stage-specific settings")}">
                <div class="pf-c-form">
                    <ak-form-element-horizontal
                        label=${msg("Bot username")}
                        required
                        name="botUsername"
                    >
                        <input
                            type="text"
                            value="${this.instance?.botUsername ?? ""}"
                            class="pf-c-form-control pf-m-monospace"
                            autocomplete="off"
                            spellcheck="false"
                            required
                        />
                        <p class="pf-c-form__helper-text">
                            ${msg("Username of the bot, as registered with @BotFather.")}
                        </p>
                    </ak-form-element-horizontal>
                    <ak-secret-text-input
                        label=${msg("Bot token")}
                        name="botToken"
                        plaintext
                        input-hint="code"
                        ?required=${!this.instance}
                        ?revealed=${!this.instance}
                        help="${msg("API token of the bot, as issued by @BotFather.")}"
                    ></ak-secret-text-input>
                    <ak-form-element-horizontal label=${msg("Mapping")} name="mapping">
                        <ak-search-select
                            .fetchObjects=${async (
                                query?: string,
                            ): Promise<NotificationWebhookMapping[]> => {
                                const args: PropertymappingsNotificationListRequest = {
                                    ordering: "name",
                                };
                                if (query) {
                                    args.search = query;
                                }
                                const items =
                                    await aki(PropertymappingsApi).propertymappingsNotificationList(
                                        args,
                                    );
                                return items.results;
                            }}
                            .renderElement=${(item: NotificationWebhookMapping): string => {
                                return item.name;
                            }}
                            .value=${(item?: NotificationWebhookMapping) => {
                                return item?.pk;
                            }}
                            .selected=${(item: NotificationWebhookMapping): boolean => {
                                return this.instance?.mapping === item.pk;
                            }}
                            blankable
                        >
                        </ak-search-select>
                        <p class="pf-c-form__helper-text">
                            ${msg("Modify the payload sent to the provider.")}
                        </p>
                    </ak-form-element-horizontal>
                    <ak-form-element-horizontal
                        label=${msg("Configuration flow")}
                        name="configureFlow"
                    >
                        <ak-search-select
                            .fetchObjects=${async (query?: string): Promise<Flow[]> => {
                                const args: FlowsInstancesListRequest = {
                                    ordering: "slug",
                                    designation: FlowDesignationEnum.StageConfiguration,
                                };
                                if (query !== undefined) {
                                    args.search = query;
                                }
                                const flows = await aki(FlowsApi).flowsInstancesList(args);
                                return flows.results;
                            }}
                            .renderElement=${(flow: Flow): string => {
                                return RenderFlowOption(flow);
                            }}
                            .renderDescription=${(flow: Flow): TemplateResult => {
                                return html`${flow.name}`;
                            }}
                            .value=${(flow: Flow | undefined): string | undefined => {
                                return flow?.pk;
                            }}
                            .selected=${(flow: Flow): boolean => {
                                return this.instance?.configureFlow === flow.pk;
                            }}
                            blankable
                        >
                        </ak-search-select>
                        <p class="pf-c-form__helper-text">
                            ${msg(
                                "Flow used by an authenticated user to configure this Stage. If empty, user will not be able to configure this stage.",
                            )}
                        </p>
                    </ak-form-element-horizontal>
                </div>
            </ak-form-group>`;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        "ak-stage-authenticator-telegram-form": AuthenticatorTelegramStageForm;
    }
}
