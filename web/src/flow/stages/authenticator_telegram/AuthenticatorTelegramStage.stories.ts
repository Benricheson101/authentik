import "@patternfly/patternfly/components/Login/login.css";
import "./AuthenticatorTelegramStage.js";

import { flowFactory } from "#stories/flow-interface";

export default {
    title: "Flow / Stages / <ak-stage-authenticator-telegram>",
};

export const Widget = flowFactory("ak-stage-authenticator-telegram", {
    codeRequired: false,
    botUsername: "authentik_bot",
    flowInfo: {
        title: "Flow Title",
    },
});

export const Code = flowFactory("ak-stage-authenticator-telegram", {
    codeRequired: true,
    botUsername: "authentik_bot",
    flowInfo: {
        title: "Flow Title",
    },
});
