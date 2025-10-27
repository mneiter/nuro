/** @type {import("eslint").Linter.Config} */
module.exports = {
  root: true,
  extends: ["next/core-web-vitals"],
  parserOptions: {
    project: "./tsconfig.json"
  },
  rules: {
    "prefer-arrow-callback": "error",
    "react/jsx-sort-props": [
      "warn",
      {
        shorthandLast: false,
        callbacksLast: true,
        ignoreCase: true,
        noSortAlphabetically: false,
        reservedFirst: true
      }
    ]
  }
};
