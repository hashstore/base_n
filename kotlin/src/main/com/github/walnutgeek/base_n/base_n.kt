package com.github.walnutgeek.base_n

import java.lang.Math.log

fun _logInt(v:Int): Int { return (log(v.toDouble()) * 10000).toInt() }

class CodecDirection (from_base:Int, to_base:Int) {
    val from_base = from_base
    val to_base = to_base
    val from_log = _logInt(from_base)
    val to_log = _logInt(to_base)

    fun aproximateSize(size:Int) { 1 + size * from_log / to_log }

    fun divmod(digits:MutableList<Int>, startAt:Int):Int{
        var remaining = 0
        for (i in startAt until digits.size) {
            val num = from_base * remaining + digits[i]
            digits[i] = num /to_base
            remaining = num % to_base
        }
        return remaining
    }
}


class Alphabet(key:String){
    val key = key;
    val inverse: Map<Char, Int> = mapOf( * key.mapIndexed { i:Int, ch:Char -> Pair(ch,i) }.toTypedArray())
    val encode_direction = CodecDirection(256, key.length)
    val decode_direction = CodecDirection(key.length, 256)
}