// copy from https://github.com/tiam-bloom/zhihuQuestionAnswer/blob/main/zhihuvmp.js thanks to tiam-bloom
// 仅供学习交流使用，严禁用于商业用途，也不要滥用，否则后果自负
// modified by relakkes

const crypto = require('crypto'); // 导入加密模块


let init_str = "6fpLRqJO8M/c3jnYxFkUVC4ZIG12SiH=5v0mXDazWBTsuw7QetbKdoPyAl+hN9rgE";
var h = {
    zk: [1170614578, 1024848638, 1413669199, -343334464, -766094290, -1373058082, -143119608, -297228157, 1933479194, -971186181, -406453910, 460404854, -547427574, -1891326262, -1679095901, 2119585428, -2029270069, 2035090028, -1521520070, -5587175, -77751101, -2094365853, -1243052806, 1579901135, 1321810770, 456816404, -1391643889, -229302305, 330002838, -788960546, 363569021, -1947871109],
    zb: [20, 223, 245, 7, 248, 2, 194, 209, 87, 6, 227, 253, 240, 128, 222, 91, 237, 9, 125, 157, 230, 93, 252, 205, 90, 79, 144, 199, 159, 197, 186, 167, 39, 37, 156, 198, 38, 42, 43, 168, 217, 153, 15, 103, 80, 189, 71, 191, 97, 84, 247, 95, 36, 69, 14, 35, 12, 171, 28, 114, 178, 148, 86, 182, 32, 83, 158, 109, 22, 255, 94, 238, 151, 85, 77, 124, 254, 18, 4, 26, 123, 176, 232, 193, 131, 172, 143, 142, 150, 30, 10, 146, 162, 62, 224, 218, 196, 229, 1, 192, 213, 27, 110, 56, 231, 180, 138, 107, 242, 187, 54, 120, 19, 44, 117, 228, 215, 203, 53, 239, 251, 127, 81, 11, 133, 96, 204, 132, 41, 115, 73, 55, 249, 147, 102, 48, 122, 145, 106, 118, 74, 190, 29, 16, 174, 5, 177, 129, 63, 113, 99, 31, 161, 76, 246, 34, 211, 13, 60, 68, 207, 160, 65, 111, 82, 165, 67, 169, 225, 57, 112, 244, 155, 51, 236, 200, 233, 58, 61, 47, 100, 137, 185, 64, 17, 70, 234, 163, 219, 108, 170, 166, 59, 149, 52, 105, 24, 212, 78, 173, 45, 0, 116, 226, 119, 136, 206, 135, 175, 195, 25, 92, 121, 208, 126, 139, 3, 75, 141, 21, 130, 98, 241, 40, 154, 66, 184, 49, 181, 46, 243, 88, 101, 183, 8, 23, 72, 188, 104, 179, 210, 134, 250, 201, 164, 89, 216, 202, 220, 50, 221, 152, 140, 33, 235, 214]

};

function i(e, t, n) {
    t[n] = 255 & e >>> 24,
        t[n + 1] = 255 & e >>> 16,
        t[n + 2] = 255 & e >>> 8,
        t[n + 3] = 255 & e
}

function Q(e, t) {
    return (4294967295 & e) << t | e >>> 32 - t
}

function B(e, t) {
    return (255 & e[t]) << 24 | (255 & e[t + 1]) << 16 | (255 & e[t + 2]) << 8 | 255 & e[t + 3]
}

function G(e) {
    var t = new Array(4)
        , n = new Array(4);
    i(e, t, 0),
        n[0] = h.zb[255 & t[0]],
        n[1] = h.zb[255 & t[1]],
        n[2] = h.zb[255 & t[2]],
        n[3] = h.zb[255 & t[3]];

    var r = B(n, 0);
    return r ^ Q(r, 2) ^ Q(r, 10) ^ Q(r, 18) ^ Q(r, 24)
}

function array_0_16_offset(e) {
    var t = new Array(16)
        , n = new Array(36);
    n[0] = B(e, 0),
        n[1] = B(e, 4),
        n[2] = B(e, 8),
        n[3] = B(e, 12);
    for (var r = 0; r < 32; r++) {
        var o = G(n[r + 1] ^ n[r + 2] ^ n[r + 3] ^ h.zk[r]);
        n[r + 4] = n[r] ^ o
    }
    return i(n[35], t, 0),
        i(n[34], t, 4),
        i(n[33], t, 8),
        i(n[32], t, 12),
        t

}

function array_16_48_offset(e, t) {
    for (var n = [], r = e.length, i = 0; 0 < r; r -= 16) {
        for (var o = e.slice(16 * i, 16 * (i + 1)), a = new Array(16), c = 0; c < 16; c++)
            a[c] = o[c] ^ t[c];
        t = array_0_16_offset(a),
            n = n.concat(t),
            i++
    }
    return n
}

function encode_0_16(array_0_16) {
    let result = [];
    let array_offset = [48, 53, 57, 48, 53, 51, 102, 55, 100, 49, 53, 101, 48, 49, 100, 55];
    for (let i = 0; i < array_0_16.length; i++) {
        let a = array_0_16[i] ^ array_offset[i],
            b = a ^ 42;
        result.push(b)
    }
    return array_0_16_offset(result)
}

function encode(ar) {
    let b = ar[1] << 8,
        c = ar[0] | b,
        d = ar[2] << 16,
        e = c | d,
        result_array = [],
        x6 = 6;
    result_array.push(e & 63);
    while (result_array.length < 4) {
        let a = e >>> x6;
        result_array.push(a & 63);
        x6 += 6;
    }
    return result_array
}

function get_init_array(encode_md5) {
    let init_array = []
    for (let i = 0; i < encode_md5.length; i++) {
        init_array.push(encode_md5.charCodeAt(i))
    }
    init_array.unshift(0)
    init_array.unshift(Math.floor(Math.random() * 127))
    while (init_array.length < 48) {
        init_array.push(14)
    }
    let array_0_16 = encode_0_16(init_array.slice(0, 16)),
        array_16_48 = array_16_48_offset(init_array.slice(16, 48), array_0_16),
        array_result = array_0_16.concat(array_16_48);
    return array_result
}

function get_zse_96(encode_md5) {
    let result_array = [],
        init_array = get_init_array(encode_md5),
        result = "";
    for (let i = 47; i >= 0; i -= 4) {
        init_array[i] ^= 58
    }
    init_array.reverse()
    for (let j = 3; j <= init_array.length; j += 3) {
        let ar = init_array.slice(j - 3, j);
        result_array = result_array.concat(encode(ar))
    }
    for (let index = 0; index < result_array.length; index++) {
        result += init_str.charAt(result_array[index])
    }
    result = '2.0_' + result
    return result
}

/***********************relakkes modify*******************************************************/

/**
 * 从cookies中提取dc0的值
 * @param cookies
 * @returns {string}
 */
const extract_dc0_value_from_cookies = function (cookies) {
    const t9 = RegExp("d_c0=([^;]+)")
    const tt = t9.exec(cookies);
    const dc0 = tt && tt[1]
    return tt && tt[1]
}

/**
 * 获取zhihu sign value 对python暴漏的接口
 * @param url 请求的路由参数
 * @param cookies 请求的cookies，需要包含dc0这个key
 * @returns {*}
 */
function get_sign(url, cookies) {
    const ta = "101_3_3.0"
    const dc0 = extract_dc0_value_from_cookies(cookies)
    const tc = "3_2.0aR_sn77yn6O92wOB8hPZnQr0EMYxc4f18wNBUgpTQ6nxERFZfTY0-4Lm-h3_tufIwJS8gcxTgJS_AuPZNcXCTwxI78YxEM20s4PGDwN8gGcYAupMWufIoLVqr4gxrRPOI0cY7HL8qun9g93mFukyigcmebS_FwOYPRP0E4rZUrN9DDom3hnynAUMnAVPF_PhaueTFH9fQL39OCCqYTxfb0rfi9wfPhSM6vxGDJo_rBHpQGNmBBLqPJHK2_w8C9eTVMO9Z9NOrMtfhGH_DgpM-BNM1DOxScLG3gg1Hre1FCXKQcXKkrSL1r9GWDXMk8wqBLNmbRH96BtOFqVZ7UYG3gC8D9cMS7Y9UrHLVCLZPJO8_CL_6GNCOg_zhJS8PbXmGTcBpgxfkieOPhNfthtf2gC_qD3YOce8nCwG2uwBOqeMoML9NBC1xb9yk6SuJhHLK7SM6LVfCve_3vLKlqcL6TxL_UosDvHLxrHmWgxBQ8Xs"
    const params_join_str = [ta, url, dc0, tc].join("+")
    const params_md5_value = crypto.createHash('md5').update(params_join_str).digest('hex')

    return {
        "x-zst-81": tc,
        "x-zse-96": get_zse_96(params_md5_value),
    }
}
