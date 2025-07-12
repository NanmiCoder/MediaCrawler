"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
exports.id = "vendor-chunks/get-proto";
exports.ids = ["vendor-chunks/get-proto"];
exports.modules = {

/***/ "(ssr)/./node_modules/get-proto/Object.getPrototypeOf.js":
/*!*********************************************************!*\
  !*** ./node_modules/get-proto/Object.getPrototypeOf.js ***!
  \*********************************************************/
/***/ ((module, __unused_webpack_exports, __webpack_require__) => {

eval("\nvar $Object = __webpack_require__(/*! es-object-atoms */ \"(ssr)/./node_modules/es-object-atoms/index.js\");\n/** @type {import('./Object.getPrototypeOf')} */ module.exports = $Object.getPrototypeOf || null;\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvZ2V0LXByb3RvL09iamVjdC5nZXRQcm90b3R5cGVPZi5qcyIsIm1hcHBpbmdzIjoiQUFBQTtBQUVBLElBQUlBLFVBQVVDLG1CQUFPQSxDQUFDO0FBRXRCLDhDQUE4QyxHQUM5Q0MsT0FBT0MsT0FBTyxHQUFHSCxRQUFRSSxjQUFjLElBQUkiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9tZWRpYWNyYXdsZXItZnJvbnRlbmQvLi9ub2RlX21vZHVsZXMvZ2V0LXByb3RvL09iamVjdC5nZXRQcm90b3R5cGVPZi5qcz9mYjM3Il0sInNvdXJjZXNDb250ZW50IjpbIid1c2Ugc3RyaWN0JztcblxudmFyICRPYmplY3QgPSByZXF1aXJlKCdlcy1vYmplY3QtYXRvbXMnKTtcblxuLyoqIEB0eXBlIHtpbXBvcnQoJy4vT2JqZWN0LmdldFByb3RvdHlwZU9mJyl9ICovXG5tb2R1bGUuZXhwb3J0cyA9ICRPYmplY3QuZ2V0UHJvdG90eXBlT2YgfHwgbnVsbDtcbiJdLCJuYW1lcyI6WyIkT2JqZWN0IiwicmVxdWlyZSIsIm1vZHVsZSIsImV4cG9ydHMiLCJnZXRQcm90b3R5cGVPZiJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/get-proto/Object.getPrototypeOf.js\n");

/***/ }),

/***/ "(ssr)/./node_modules/get-proto/Reflect.getPrototypeOf.js":
/*!**********************************************************!*\
  !*** ./node_modules/get-proto/Reflect.getPrototypeOf.js ***!
  \**********************************************************/
/***/ ((module) => {

eval("\n/** @type {import('./Reflect.getPrototypeOf')} */ module.exports = typeof Reflect !== \"undefined\" && Reflect.getPrototypeOf || null;\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvZ2V0LXByb3RvL1JlZmxlY3QuZ2V0UHJvdG90eXBlT2YuanMiLCJtYXBwaW5ncyI6IkFBQUE7QUFFQSwrQ0FBK0MsR0FDL0NBLE9BQU9DLE9BQU8sR0FBRyxPQUFRQyxZQUFZLGVBQWVBLFFBQVFDLGNBQWMsSUFBSyIsInNvdXJjZXMiOlsid2VicGFjazovL21lZGlhY3Jhd2xlci1mcm9udGVuZC8uL25vZGVfbW9kdWxlcy9nZXQtcHJvdG8vUmVmbGVjdC5nZXRQcm90b3R5cGVPZi5qcz8zYjI1Il0sInNvdXJjZXNDb250ZW50IjpbIid1c2Ugc3RyaWN0JztcblxuLyoqIEB0eXBlIHtpbXBvcnQoJy4vUmVmbGVjdC5nZXRQcm90b3R5cGVPZicpfSAqL1xubW9kdWxlLmV4cG9ydHMgPSAodHlwZW9mIFJlZmxlY3QgIT09ICd1bmRlZmluZWQnICYmIFJlZmxlY3QuZ2V0UHJvdG90eXBlT2YpIHx8IG51bGw7XG4iXSwibmFtZXMiOlsibW9kdWxlIiwiZXhwb3J0cyIsIlJlZmxlY3QiLCJnZXRQcm90b3R5cGVPZiJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/get-proto/Reflect.getPrototypeOf.js\n");

/***/ }),

/***/ "(ssr)/./node_modules/get-proto/index.js":
/*!*****************************************!*\
  !*** ./node_modules/get-proto/index.js ***!
  \*****************************************/
/***/ ((module, __unused_webpack_exports, __webpack_require__) => {

eval("\nvar reflectGetProto = __webpack_require__(/*! ./Reflect.getPrototypeOf */ \"(ssr)/./node_modules/get-proto/Reflect.getPrototypeOf.js\");\nvar originalGetProto = __webpack_require__(/*! ./Object.getPrototypeOf */ \"(ssr)/./node_modules/get-proto/Object.getPrototypeOf.js\");\nvar getDunderProto = __webpack_require__(/*! dunder-proto/get */ \"(ssr)/./node_modules/dunder-proto/get.js\");\n/** @type {import('.')} */ module.exports = reflectGetProto ? function getProto(O) {\n    // @ts-expect-error TS can't narrow inside a closure, for some reason\n    return reflectGetProto(O);\n} : originalGetProto ? function getProto(O) {\n    if (!O || typeof O !== \"object\" && typeof O !== \"function\") {\n        throw new TypeError(\"getProto: not an object\");\n    }\n    // @ts-expect-error TS can't narrow inside a closure, for some reason\n    return originalGetProto(O);\n} : getDunderProto ? function getProto(O) {\n    // @ts-expect-error TS can't narrow inside a closure, for some reason\n    return getDunderProto(O);\n} : null;\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKHNzcikvLi9ub2RlX21vZHVsZXMvZ2V0LXByb3RvL2luZGV4LmpzIiwibWFwcGluZ3MiOiJBQUFBO0FBRUEsSUFBSUEsa0JBQWtCQyxtQkFBT0EsQ0FBQztBQUM5QixJQUFJQyxtQkFBbUJELG1CQUFPQSxDQUFDO0FBRS9CLElBQUlFLGlCQUFpQkYsbUJBQU9BLENBQUM7QUFFN0Isd0JBQXdCLEdBQ3hCRyxPQUFPQyxPQUFPLEdBQUdMLGtCQUNkLFNBQVNNLFNBQVNDLENBQUM7SUFDcEIscUVBQXFFO0lBQ3JFLE9BQU9QLGdCQUFnQk87QUFDeEIsSUFDRUwsbUJBQ0MsU0FBU0ksU0FBU0MsQ0FBQztJQUNwQixJQUFJLENBQUNBLEtBQU0sT0FBT0EsTUFBTSxZQUFZLE9BQU9BLE1BQU0sWUFBYTtRQUM3RCxNQUFNLElBQUlDLFVBQVU7SUFDckI7SUFDQSxxRUFBcUU7SUFDckUsT0FBT04saUJBQWlCSztBQUN6QixJQUNFSixpQkFDQyxTQUFTRyxTQUFTQyxDQUFDO0lBQ3BCLHFFQUFxRTtJQUNyRSxPQUFPSixlQUFlSTtBQUN2QixJQUNFIiwic291cmNlcyI6WyJ3ZWJwYWNrOi8vbWVkaWFjcmF3bGVyLWZyb250ZW5kLy4vbm9kZV9tb2R1bGVzL2dldC1wcm90by9pbmRleC5qcz81YTEzIl0sInNvdXJjZXNDb250ZW50IjpbIid1c2Ugc3RyaWN0JztcblxudmFyIHJlZmxlY3RHZXRQcm90byA9IHJlcXVpcmUoJy4vUmVmbGVjdC5nZXRQcm90b3R5cGVPZicpO1xudmFyIG9yaWdpbmFsR2V0UHJvdG8gPSByZXF1aXJlKCcuL09iamVjdC5nZXRQcm90b3R5cGVPZicpO1xuXG52YXIgZ2V0RHVuZGVyUHJvdG8gPSByZXF1aXJlKCdkdW5kZXItcHJvdG8vZ2V0Jyk7XG5cbi8qKiBAdHlwZSB7aW1wb3J0KCcuJyl9ICovXG5tb2R1bGUuZXhwb3J0cyA9IHJlZmxlY3RHZXRQcm90b1xuXHQ/IGZ1bmN0aW9uIGdldFByb3RvKE8pIHtcblx0XHQvLyBAdHMtZXhwZWN0LWVycm9yIFRTIGNhbid0IG5hcnJvdyBpbnNpZGUgYSBjbG9zdXJlLCBmb3Igc29tZSByZWFzb25cblx0XHRyZXR1cm4gcmVmbGVjdEdldFByb3RvKE8pO1xuXHR9XG5cdDogb3JpZ2luYWxHZXRQcm90b1xuXHRcdD8gZnVuY3Rpb24gZ2V0UHJvdG8oTykge1xuXHRcdFx0aWYgKCFPIHx8ICh0eXBlb2YgTyAhPT0gJ29iamVjdCcgJiYgdHlwZW9mIE8gIT09ICdmdW5jdGlvbicpKSB7XG5cdFx0XHRcdHRocm93IG5ldyBUeXBlRXJyb3IoJ2dldFByb3RvOiBub3QgYW4gb2JqZWN0Jyk7XG5cdFx0XHR9XG5cdFx0XHQvLyBAdHMtZXhwZWN0LWVycm9yIFRTIGNhbid0IG5hcnJvdyBpbnNpZGUgYSBjbG9zdXJlLCBmb3Igc29tZSByZWFzb25cblx0XHRcdHJldHVybiBvcmlnaW5hbEdldFByb3RvKE8pO1xuXHRcdH1cblx0XHQ6IGdldER1bmRlclByb3RvXG5cdFx0XHQ/IGZ1bmN0aW9uIGdldFByb3RvKE8pIHtcblx0XHRcdFx0Ly8gQHRzLWV4cGVjdC1lcnJvciBUUyBjYW4ndCBuYXJyb3cgaW5zaWRlIGEgY2xvc3VyZSwgZm9yIHNvbWUgcmVhc29uXG5cdFx0XHRcdHJldHVybiBnZXREdW5kZXJQcm90byhPKTtcblx0XHRcdH1cblx0XHRcdDogbnVsbDtcbiJdLCJuYW1lcyI6WyJyZWZsZWN0R2V0UHJvdG8iLCJyZXF1aXJlIiwib3JpZ2luYWxHZXRQcm90byIsImdldER1bmRlclByb3RvIiwibW9kdWxlIiwiZXhwb3J0cyIsImdldFByb3RvIiwiTyIsIlR5cGVFcnJvciJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(ssr)/./node_modules/get-proto/index.js\n");

/***/ })

};
;