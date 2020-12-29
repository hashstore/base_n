package com.github.walnutgeek.base_n

import java.lang.Math.log
import java.math.BigInteger
import java.security.MessageDigest
import kotlin.math.ln

val ALPHABETS = mapOf(
    2 to "01",
    8 to "01234567",
    11 to "0123456789a",
    16 to "0123456789abcdef",
    32 to "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    36 to "0123456789abcdefghijklmnopqrstuvwxyz",
    58 to "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
    62 to "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    64 to "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
    67 to "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~"
)

private fun sha256x2(input: ByteArray): ByteArray = sha256(sha256(input))

private fun sha256(input: ByteArray) = MessageDigest.getInstance("SHA-256").digest(input)

private fun logInt(v:Int): Int = (ln(v.toDouble()) * 10000).toInt()

class CodecDirection (val fromBase:Int, val toBase :Int) {
    val fromLog = logInt(fromBase)
    val toLog = logInt(toBase)

    fun approximateSize(size:Int):Int = 1 + size * fromLog / toLog

    fun divmod(digits:IntArray, startAt:Int):Int{
        var remaining = 0
        for (i in startAt until digits.size) {
            val num = fromBase * remaining + digits[i]
            digits[i] = num / toBase
            remaining = num % toBase
        }
        return remaining
    }
}


class Alphabet private constructor(val key:String){
    companion object Factory {
        private val cache = mutableMapOf<String,Alphabet>()

        fun predefined(id: Int) : Alphabet {
            return fromString(ALPHABETS[id]!!)
        }

        fun fromString(key : String) : Alphabet {
            return cache[key] ?: Alphabet(key).also{ cache[key] = it }
        }
    }
    val inverse: Map<Char, Int> = mapOf( *key.mapIndexed { i:Int, ch:Char -> ch to i }.toTypedArray())
    val encoder = CodecDirection(256, key.length)
    val decoder = CodecDirection(key.length, 256)

    fun toDigits(chars: String):IntArray = IntArray (chars.length) {
            i-> inverse[chars[i]] ?:
            throw java.lang.IndexOutOfBoundsException("'${chars[i]}' not in alphabet")}

    fun toChars(digits:IntArray ):String = String(CharArray(digits.size) {
            i-> digits[i].let {
                if ( it < key.length )
                    key[it]
                else
                    throw java.lang.IndexOutOfBoundsException("digit:${it} not in alphabet")
            }})

}

tailrec fun countLeadingZeros(digits: IntArray, z: Int = 0): Int {
    return if (z < digits.size && digits[z] == 0) countLeadingZeros(digits, z+1) else z
}

abstract class BaseN {
    abstract val alphabet:Alphabet

    fun encode(bytes:ByteArray):String = alphabet.toChars(
            codeDigits( IntArray(bytes.size){ i-> bytes[i].toInt() and 0xFF}, alphabet.encoder))

    fun decode(text:String):ByteArray = codeDigits(alphabet.toDigits(text), alphabet.decoder).let{
        ByteArray(it.size) {i->it[i].toByte()}}

    fun codeDigits( digits:IntArray,  direction:CodecDirection):IntArray {
        if (digits.isEmpty()) return IntArray(0)
        val leadingZeros = countLeadingZeros(digits)
        val codeSize = direction.approximateSize(digits.size - leadingZeros)
        val out= IntArray(leadingZeros + codeSize)
        val firstNonZero = repackDigits(digits, direction, leadingZeros, out)
        return if (firstNonZero == leadingZeros ) out else out.copyOfRange(firstNonZero - leadingZeros,out.size)
    }

    abstract fun repackDigits( digits:IntArray,  direction:CodecDirection, leadingZeros:Int, out:IntArray):Int

    fun encodeCheck( bytes:ByteArray): String {
        val buffer = ByteArray(bytes.size + 4)
        bytes.copyInto(buffer)
        val checksum = sha256x2(bytes)
        checksum.copyInto(buffer, bytes.size, endIndex = 4)
        return encode(buffer)
    }

    fun decodeCheck(code:String) :ByteArray{
        val bytes = decode(code)
        val payloadEnd = bytes.size - 4
        val buffer = ByteArray(payloadEnd) {i->bytes[i]}
        val checksum = sha256x2(buffer).slice(0..3)
        if (checksum != bytes.slice(payloadEnd until bytes.size) ) {
            throw IllegalStateException("Checksum does not match")
        }
        return buffer
    }

}


class LoopBaseN(override val alphabet:Alphabet) : BaseN() {

    override fun repackDigits(digits:IntArray, direction:CodecDirection, leadingZeros:Int, out:IntArray): Int {
        var startAt = leadingZeros
        var j = out.size
        var firstNonZero = j
        while (startAt < digits.size && leadingZeros < j) {
            val mod = direction.divmod(digits, startAt)
            if (digits[startAt] == 0) startAt++
            out[--j] = mod
            if (mod != 0) firstNonZero = j
        }
        return firstNonZero
    }
}

class BigIntBaseN(override val alphabet:Alphabet) : BaseN() {

    override fun repackDigits(digits:IntArray, direction:CodecDirection, leadingZeros:Int,
                              out:IntArray): Int {
        val fromBase = BigInteger.valueOf(direction.fromBase.toLong())
        val toBase = BigInteger.valueOf(direction.toBase.toLong())
        var acc = digits.slice(leadingZeros until digits.size)
                .fold(BigInteger.ZERO) {p, n -> p * fromBase + BigInteger.valueOf(n.toLong()) }
        var j = out.size
        var firstNonZero = j
        while (acc > BigInteger.ZERO) {
            val (newAcc,bigMod) = acc.divideAndRemainder(toBase)
            val mod = bigMod.toInt()
            acc = newAcc
            out[--j] = mod
            if (mod != 0) firstNonZero = j
        }
        return firstNonZero
    }
}
