document.addEventListener(
    "DOMContentLoaded",
    function () {

        const passwordToggles =
            document.querySelectorAll(".password-toggle");

        passwordToggles.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const targetId =
                            button.dataset.passwordTarget;

                        const input =
                            document.getElementById(targetId);

                        if (!input) {
                            return;
                        }

                        const passwordVisible =
                            input.type === "text";

                        if (passwordVisible) {

                            input.type = "password";

                            button.setAttribute(
                                "aria-label",
                                "Show password"
                            );

                            button.setAttribute(
                                "title",
                                "Show password"
                            );

                        } else {

                            input.type = "text";

                            button.setAttribute(
                                "aria-label",
                                "Hide password"
                            );

                            button.setAttribute(
                                "title",
                                "Hide password"
                            );

                        }

                    }
                );

            }
        );

    }
);